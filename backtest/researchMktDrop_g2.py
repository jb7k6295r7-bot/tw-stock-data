# -*- coding: utf-8 -*-
"""大跌 4 檔 × 情報線 G2「大跌先買指數、止跌再換個股」三臂描述（⛔ 不計 N、⛔ 不判定、⛔ 不是買賣建議）——回測線計算子代理，2026-11-07。
依據：情報線 2026-11-07 22:58 件（使用者 11/7 22:53「都做」；股癌借鏡第二批第 5 件）。情報線登錄 claude/prereg_gooaye_batch_20261107.md G2、
      結果 sources/gooaye_batch_results_20261107.md：⚠ 本機 WSL／Windows 與 tw-stock-data 各分支都找不到這兩檔 ⇒ 口徑照信件；
      情報線判語事先固定「還沒測（依構造，事件 < 24）」⇒ 本件也只描述。
⛔ 只計算：不 commit、不 push、不寫跨線信箱、不改既有檔（researchMktDrop／_v1／_addon2／_f9 只 import 重用；v1 逐股快取只讀）；用語「假訊號」。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchMktDrop_g2 [--procs 3]

═══ 口徑（照信件＋大跌 4 檔既有規則；寫死於第一次跑之前，2026-11-07 台北）═══
 G0 事件 ＝ V1.index_events q2 接受事件（擴張視窗最差 2%、前 20 日沒有別的大跌日、同時只處理一個事件）；世界 ＝ v1 主世界（個股快照 2026-09-24）
    ⇒ 2015 起 18 事件（2015～2021 7、2022～ 11）；2026-10-15（前瞻第 0 筆）在快照之後 ⇒ 不進統計，另列前瞻帳面（每日名單第八節，未扣成本）
    早年（2006～2014）10 事件：大跌 4 檔（F9）算不出（Q 無早年財報、F7 法人／融資 2015 起）⇒ 不列；情報線也只從 2015 起
 G1 三臂（同事件、同出場；事件日 t 收盤決定）：
    E0 ＝ t＋1 開盤買 0050（＝ v1 候選 A）；
    S4 ＝ t＋1 開盤等權買大跌 4 檔 ＝ F9 前 4（f9/features.csv、F9.order；C＋ 內 F6＋F7＋Q 名次）；買不到剔除、全買不到 ⇒ 0（同 addon2）
    M4 ＝ t＋1 開盤買 0050；第一次「連 5 個交易日加權不創事件以來新低」的第 5 天 k 收盤決定 ⇒ k＋1 開盤賣 0050、全部換成同 4 檔（等權）
 G2 出場一律照大跌 4 檔主出場：加權收盤 ≥ 事件前一日收盤的第一天 D0 ⇒ D0 之後第一根可賣開盤全賣（鎖跌停順延）；個股壞根前一根收盤強制賣、
    下市最後收盤（MD.exits_core）；⛔ 不設天數。M4 的 4 檔 ＝ addon2 主臂同法：exit_job 把 k 欄的收復日換成 D0 重算（逐股出場對帳 v1 快取）
 G3 成本：個股 0.585%、ETF 0.385% 來回；M4 換股 ⇒ 0050 來回 ＋ 4 檔來回都扣（淨 ＝ (1＋g0050)(1−0.385%)×(1＋g4檔)(1−0.585%) − 1）；未含滑價
 ★ 執行者定（第一次跑之前）：
    ① 「不創新低」用加權【收盤】（market_index.csv 只有收盤）；新低 ＝ 收盤 ＜ 事件日起（含事件日）到前一日的最低收盤；平盤（＝最低）不算新低
    ② 連 5 日從 t＋1 起算（事件日本身不算）⇒ 最早 k ＝ t＋5、t＋6 開盤換；中途創新低 ⇒ 計數歸零
    ③ D0 ≤ k（換股訊號當天或之前已收復）⇒ 不換股、M4 ＝ E0（記「換股前已收復」）；D0 ＝ k ⇒ 同一個開盤，出場優先
    ④ 換股日 4 檔買不到（沒成交、開盤漲停鎖死、壞根）⇒ 剔除、其餘等權；4 檔全買不到 ⇒ 不換、續抱 0050 到出場（記「換股買不到」）
    ⑤ 換股日 0050 開盤缺 ⇒ 用前一日收盤（同 V1.curve2）
    ⑥ 持有中最大跌幅（日收盤盯市、毛、未扣成本）兩種都報：主 ＝ 最低帳面（相對投入，≥0 記 0；＝ addon2「最大帳面虧損」）；
       另 ＝ 峰谷回落（相對持有中最高帳面）；M4 路徑 ＝ 換股前 0050 收盤÷買價、換股日起 （0050 賣價÷買價）×4 檔等權（已賣固定在賣價）
    ⑦ 持有天數 ＝ 買進根到最後一份賣出根（世界日曆位置差；＝ addon2「不加碼_持有天數」）
    ⑧ 描述對照（只並列、不改口徑）：C＋ 全買（≈ 情報線「整籃」：跌最深一成 ∧ 營收年增 ＞ 0）與「先 0050 再換 C＋ 全買」（同 M4 規則，籃子換成 C＋）；
       加碼那份 ＝ 既有 addon2（T2 收盤比事件日再跌 ≥5%、乙＝加碼同一批、主出場）的 E0、S4、C＋ 加碼後報酬，另列；M4 無既有加碼定義 ⇒ 不做
 對帳（不過 ⇒ 停）：E0、S4、C＋ 的報酬、最低帳面、持有天數 ＝ addon2/event_rows.csv（不加碼欄；該檔存 8 位有效數字 ⇒ 容差 1e-7）；exit_job 原收復日出場 ＝ v1 快取；
    M4 未換股的事件 ＝ E0 逐位元同
── 事後註（照實記）──
 ① 第一次跑停在 E0 對帳（差 4.8e-9 ＞ 原容差 1e-9）：addon2/event_rows.csv 是 8 位有效數字存檔 ⇒ 容差改 1e-7 重跑；
    停在任何臂的彙總之前（執行者沒看到結果）；⛔ 事件、選股、換股、出場、成本規則都沒改
輸出 backtest/resultsMktDrop/g2/：events.csv（逐事件）、summary.csv、G2.json、結果.md、run.log
"""
from __future__ import annotations

import argparse
import json
import os
import pickle
import sys
import time

import numpy as np
import pandas as pd

REPO = os.path.expanduser("~/tw-p17")
sys.path.insert(0, REPO)
OUT = os.path.join(REPO, "backtest/resultsMktDrop/g2")
V1WORK = os.path.expanduser("~/mktdropwork/v1")
RD = os.path.join(REPO, "backtest/resultsMktDrop")
TIME = "2026-11-07（台北；口徑寫死、第一次跑之前）"
NSTREAK = 5
N4 = 4
COST_STK, COST_ETF = 0.00585, 0.00385
INTEL = {"E0": 0.0240, "整籃": 0.0712, "先0050再換整籃": 0.0530, "整籃最大跌幅最差": -0.351, "事件數": 19}
ARMS = ["E0", "S4", "M4", "CP", "MCP"]
AN = {"E0": "E0 0050", "S4": "S4 大跌 4 檔（F9 前 4）", "M4": "M4 先 0050、止跌換 4 檔",
      "CP": "（對照）C＋ 全買", "MCP": "（對照）先 0050、止跌換 C＋ 全買"}


def now_tpe():
    return pd.Timestamp.now(tz="Asia/Taipei").strftime("%Y-%m-%d %H:%M")


def swap_row(cl, i0, nstreak=NSTREAK):
    """⇒ 第一次「連 nstreak 個交易日收盤不創事件以來新低」的第 nstreak 天（指數列）；沒有 ⇒ None。★①②"""
    low = cl[i0]; st = 0
    for j in range(i0 + 1, len(cl)):
        if cl[j] < low:
            low = cl[j]; st = 0
        else:
            st += 1
            if st >= nstreak:
                return j
    return None


def dd_stats(V):
    V = np.asarray(V, float)
    mn = float(min(0.0, np.nanmin(V) - 1.0))
    pk = np.maximum.accumulate(np.r_[1.0, V])[1:]
    return mn, float(np.nanmin(V / pk - 1.0))


def run(a, log):
    T0 = time.time(); os.makedirs(OUT, exist_ok=True)
    from multiprocessing import Pool
    from backtest import researchMktDrop as MD
    from backtest import researchMktDrop_v1 as V1
    from backtest import researchMktDrop_addon2 as A2
    from backtest import researchMktDrop_f9 as F9
    MD.SEGS = V1.SEGS_V1
    S = {"件": "大跌 4 檔 × G2 先指數再換股（描述、不計 N、不判定）", "口徑寫死": TIME, "開跑（台北）": now_tpe(), "臂": AN, "對帳": {}}
    REC = []

    def rec(name, val, ok):
        REC.append({"對帳": name, "值": val, "通過": bool(ok)}); log(f"[對帳] {name}：{val}｜{'✔' if ok else '✘'}")
        if not ok:
            raise SystemExit(f"⛔ 對帳不過：{name} {val}")

    IXmd = MD.load_index(log); df = IXmd["df"]; EV = V1.index_events(df); cl = EV["cl"]
    ft = np.flatnonzero(EV["FIRST"]["q2"])
    if not np.array_equal(EV["rec"][ft], IXmd["rec"][ft]):
        raise SystemExit("⛔ q2 收復列與初測 rec 不同")
    S["指數"] = {"origin/main sha": IXmd["sha"], "期間": f"{df['date'].iloc[0].date()}～{df['date'].iloc[-1].date()}"}
    A2R = pd.read_csv(os.path.join(RD, "addon2/event_rows.csv"))
    A2R = A2R[(A2R["世界"] == "主") & (A2R["觸發"] == "T2") & (A2R["方式"] == "乙") & (A2R["出場"] == "主")]
    F9F = pd.read_csv(os.path.join(RD, "f9/features.csv"), dtype={"sid": str})
    FF = pd.read_csv(os.path.join(RD, "fund/features.csv"), dtype={"sid": str}); FF["買得到"] = FF["買得到"].astype(str).str.lower().eq("true")

    wn = "主"
    W = MD.load_world(wn, IXmd, log); MD._G[wn] = W; A2._G[wn] = W
    PK = pickle.load(open(os.path.join(V1WORK, f"packs_{wn}.pkl"), "rb")); log("[逐股] 讀 v1 快取（只讀）")
    EP = {s: MD.etf_pack(W, s) for s in MD.ETFS}
    M = MD.assemble(W, PK, EP, log)
    del PK
    cal = W["cal"]; n0 = W["n0"]; Sx = M["S"]; rix = {s: r for r, s in enumerate(M["sids"])}
    BO, BC = W["BO"], W["BC"]
    datepos = {d: j for j, d in enumerate(cal)}
    segof = lambda p: next((sg for sg, (x0, y0) in W["segp"].items() if x0 <= p <= y0), None)   # noqa: E731
    evs = []
    for i in np.flatnonzero(EV["ACC"]["q2"]):
        p = datepos.get(df["date"].iloc[i])
        if p is not None and p + 1 < n0 and segof(p) is not None:
            evs.append((p, int(i)))
    S["世界尾後的接受事件（不進統計）"] = [str(df["date"].iloc[i].date()) for i in np.flatnonzero(EV["ACC"]["q2"]) if df["date"].iloc[i] > cal[-1]]
    log(f"[事件] 主世界 {len(evs)}｜世界尾後 {S['世界尾後的接受事件（不進統計）']}")

    # ── 換股訊號（指數）──
    SW = {}
    Darr_main = W["Darr"].copy()
    need = set()
    for p, i in evs:
        D0 = int(EV["rec"][i]) if EV["rec"][i] >= 0 else len(df)
        k = swap_row(cl, i)
        o = {"D0": D0, "k": k, "pk": None, "狀態": None}
        if k is None or D0 <= k:
            o["狀態"] = "換股前已收復" if (k is None or D0 <= k) and D0 < len(df) else "沒有換股訊號"
        else:
            pk = datepos.get(df["date"].iloc[k])
            if pk is None or pk + 1 >= n0:
                o["狀態"] = "換股日在世界外"
            else:
                o["pk"] = pk; o["狀態"] = "換股"
                Darr_main[pk] = W["Darr"][p]
                top = F9.order(F9F[F9F["事件日"] == str(cal[p].date())], "F9").head(N4)["sid"].tolist()
                need |= set(top) | set(FF.loc[FF["事件日"] == str(cal[p].date()), "sid"])
        SW[p] = o
    A2._G["Darr_main_" + wn] = Darr_main
    t1 = time.time()
    with Pool(a.procs) as pool:
        RES = dict(pool.imap_unordered(A2.exit_job, [(wn, s) for s in sorted(need)], chunksize=8))
    PKc = pickle.load(open(os.path.join(V1WORK, f"packs_{wn}.pkl"), "rb"))
    SPa = M["SP"]["主"].copy(); SXa = M["SX"]["主"].copy(); SKa = M["SK"]["主"].copy(); bad0 = 0
    for s, v in RES.items():
        idx, e0, e1 = v
        sp0, sx0, kd0 = PKc[s]["ex"]["主"]
        if not (np.array_equal(e0[0], sp0) and np.array_equal(np.nan_to_num(e0[1], nan=-9), np.nan_to_num(sx0, nan=-9)) and np.array_equal(e0[2], kd0)):
            bad0 += 1
        r = rix[s]; SPa[r, idx] = e1[0]; SXa[r, idx] = e1[1]; SKa[r, idx] = e1[2]
    del PKc
    rec(f"exit_job 原收復日出場 ＝ v1 快取（{len(RES)} 檔）", bad0, bad0 == 0)
    log(f"[換股欄出場重算] {len(RES)} 檔｜{time.time() - t1:.0f}s")
    Mm = dict(M); Mm["SP"] = {"主": SPa}; Mm["SX"] = {"主": SXa}; Mm["SK"] = {"主": SKa}

    def leg(Mx, I, t, cost):
        """⇒ (淨報酬, 毛報酬, V 路徑, e, end) ；I 空 ⇒ None。"""
        if not len(I):
            return None
        P_, e, end, sp, kd, g = A2.spath(W, Mx, I, t)
        gm = float(np.mean(g))
        return (1 + gm) * (1 - cost) - 1, gm, np.nanmean(P_, axis=0), e, end

    ROWS = []
    for p, i in evs:
        ds = str(cal[p].date()); sg = segof(p); o = SW[p]
        top = F9.order(F9F[F9F["事件日"] == ds], "F9").head(N4)["sid"].tolist()
        r4 = np.array([rix[s] for s in top], int)
        cpl = FF[FF["事件日"] == ds]; rcp = np.array([rix[s] for s in cpl["sid"]], int)
        bchk = int(np.sum(M["BUY"][rcp, p] != cpl["買得到"].to_numpy(bool)))
        S["對帳"]["C＋ 買得到 vs fund 不同（檔次）"] = S["對帳"].get("C＋ 買得到 vs fund 不同（檔次）", 0) + bchk
        row = {"段": sg, "年": cal[p].year, "事件日": ds, "指數報酬": float(EV["r"][i]),
               "收復日": (str(df["date"].iloc[o["D0"]].date()) if o["D0"] < len(df) else None), "收復等待（指數交易日）": (o["D0"] - i if o["D0"] < len(df) else None),
               "持有中最低收盤相對事件日": float(cl[i + 1:o["D0"]].min() / cl[i] - 1) if o["D0"] > i + 1 else 0.0,
               "換股訊號日（第 5 天）": (str(df["date"].iloc[o["k"]].date()) if o["k"] is not None else None),
               "換股日（開盤）": (str(cal[o["pk"] + 1].date()) if o["pk"] is not None else None), "M4 狀態": o["狀態"],
               "換股前已收復": o["狀態"] == "換股前已收復", "4 檔": " ".join(top), "C＋ 檔數": len(rcp)}
        I0 = np.array([Sx]) if M["BUY"][Sx, p] else np.array([], int)
        base = {}
        for arm, I, cost in (("E0", I0, COST_ETF), ("S4", r4[M["BUY"][r4, p]], COST_STK), ("CP", rcp[M["BUY"][rcp, p]], COST_STK)):
            L = leg(M, I, p, cost)
            if L is None:
                row.update({f"{arm}_報酬": 0.0, f"{arm}_最低帳面": 0.0, f"{arm}_峰谷回落": 0.0, f"{arm}_持有天數": 0.0, f"{arm}_買到檔數": 0}); continue
            net, gm, V, e, end = L; mn, pkdd = dd_stats(V); base[arm] = L
            row.update({f"{arm}_報酬": net, f"{arm}_最低帳面": mn, f"{arm}_峰谷回落": pkdd, f"{arm}_持有天數": float(end - e), f"{arm}_買到檔數": int(len(I)),
                        f"{arm}_賣完日": str(cal[end].date())})
        # 對帳 addon2（不加碼欄）
        for arm, cd in (("E0", "A"), ("S4", "F9"), ("CP", "C+")):
            q = A2R[(A2R["候選"] == cd) & (A2R["事件日"] == ds)]
            if len(q) != 1:
                raise SystemExit(f"⛔ addon2 沒有 {ds} {cd}")
            q = q.iloc[0]
            d_ = max(abs(q["不加碼_報酬"] - row[f"{arm}_報酬"]), abs(q["不加碼_最大帳面虧損"] - row[f"{arm}_最低帳面"]), abs(q["不加碼_持有天數"] - row[f"{arm}_持有天數"]))
            S["對帳"][f"{arm} vs addon2 最大差"] = max(S["對帳"].get(f"{arm} vs addon2 最大差", 0.0), float(d_))
            row[f"{arm}＋−5%加碼_有觸發"] = bool(q["有觸發"]); row[f"{arm}＋−5%加碼_報酬（既有 addon2）"] = float(q["加碼後_報酬"])
            if bool(q["有觸發"]) and isinstance(q.get("加碼後_最大帳面虧損"), float):
                row[f"{arm}＋−5%加碼_最低帳面（既有 addon2）"] = float(q["加碼後_最大帳面虧損"])
        # M4／MCP
        for arm, rows_, cost in (("M4", r4, COST_STK), ("MCP", rcp, COST_STK)):
            E0L = base.get("E0")
            pk = o["pk"]
            I2 = rows_[M["BUY"][rows_, pk]] if pk is not None else np.array([], int)
            if pk is None or not len(I2) or E0L is None:
                if pk is not None and not len(I2):
                    row[f"{arm}_狀態"] = "換股買不到、續抱 0050"
                for c in ("報酬", "最低帳面", "峰谷回落", "持有天數"):
                    row[f"{arm}_{c}"] = row[f"E0_{c}"]
                row[f"{arm}_換股"] = False
                continue
            e = p + 1; s = pk + 1
            bp0 = M["BP"][Sx, p]
            o0 = BO[s] if np.isfinite(BO[s]) and BO[s] > 0 else BC[s - 1]
            g0 = o0 / bp0 - 1.0
            net2, g4, V2, e2, end2 = leg(Mm, I2, pk, cost)
            if e2 != s:
                raise SystemExit(f"⛔ {ds} 換股進場位置 {e2} ≠ {s}")
            net = (1 + g0) * (1 - COST_ETF) * (1 + g4) * (1 - cost) - 1
            V = np.r_[M["C"][Sx, e:s] / bp0, (1 + g0) * V2]
            mn, pkdd = dd_stats(V)
            row.update({f"{arm}_報酬": net, f"{arm}_最低帳面": mn, f"{arm}_峰谷回落": pkdd, f"{arm}_持有天數": float(end2 - e), f"{arm}_換股": True,
                        f"{arm}_0050段毛報酬": float(g0), f"{arm}_換股後籃子毛報酬": float(g4), f"{arm}_換股買到檔數": int(len(I2)),
                        f"{arm}_換股前最低帳面": float(min(0.0, np.nanmin(M["C"][Sx, e:s] / bp0) - 1)), f"{arm}_賣完日": str(cal[end2].date())})
        ROWS.append(row)
    ER = pd.DataFrame(ROWS)
    rec("E0 ＝ addon2 A 不加碼（報酬／最低帳面／持有天數 最大差）", S["對帳"]["E0 vs addon2 最大差"], S["對帳"]["E0 vs addon2 最大差"] < 1e-7)
    rec("S4 ＝ addon2 F9 不加碼（最大差）", S["對帳"]["S4 vs addon2 最大差"], S["對帳"]["S4 vs addon2 最大差"] < 1e-7)
    rec("C＋ ＝ addon2 C+ 不加碼（最大差）", S["對帳"]["CP vs addon2 最大差"], S["對帳"]["CP vs addon2 最大差"] < 1e-7)
    rec("C＋ 買得到 ＝ fund/features（不同檔次）", S["對帳"]["C＋ 買得到 vs fund 不同（檔次）"], S["對帳"]["C＋ 買得到 vs fund 不同（檔次）"] == 0)
    nsw = ER[~ER["M4_換股"]]
    dm = float(np.max(np.abs(nsw["M4_報酬"] - nsw["E0_報酬"]))) if len(nsw) else 0.0
    rec(f"M4 未換股事件 ＝ E0（{len(nsw)} 件）", dm, dm == 0.0)

    # ── 彙總 ──
    SUM = []
    groups = [("2015～（18 事件）", ER), ("2015～2021", ER[ER["段"] == "2015～2021"]), ("2022～", ER[ER["段"] == "2022～"])]
    for gname, G in groups:
        for arm in ARMS:
            v = G[f"{arm}_報酬"].to_numpy(float)
            SUM.append({"段": gname, "臂": AN[arm], "事件數": len(G), "年分群數": int(G["年"].nunique()), "平均": float(v.mean()), "中位數": float(np.median(v)),
                        "勝率": float(np.mean(v > 0)), "最差報酬": float(v.min()), "最低帳面_平均": float(G[f"{arm}_最低帳面"].mean()),
                        "最低帳面_最差（最大跌幅）": float(G[f"{arm}_最低帳面"].min()), "峰谷回落_最差": float(G[f"{arm}_峰谷回落"].min()),
                        "平均持有天數": float(G[f"{arm}_持有天數"].mean()), "最長持有天數": float(G[f"{arm}_持有天數"].max()),
                        "年分群平均（每年等權）": float(G.groupby("年")[f"{arm}_報酬"].mean().mean())})
        for arm in ("E0", "S4", "CP"):
            v = G[f"{arm}＋−5%加碼_報酬（既有 addon2）"].to_numpy(float)
            SUM.append({"段": gname, "臂": f"（另列）{AN[arm]}＋−5% 加碼（既有 addon2 T2 乙 主）", "事件數": len(G), "年分群數": int(G["年"].nunique()),
                        "平均": float(v.mean()), "中位數": float(np.median(v)), "勝率": float(np.mean(v > 0)), "最差報酬": float(v.min()),
                        "加碼有觸發事件數": int(G[f"{arm}＋−5%加碼_有觸發"].sum())})
    SU = pd.DataFrame(SUM)
    ER.to_csv(os.path.join(OUT, "events.csv"), index=False, float_format="%.6g", encoding="utf-8")
    SU.to_csv(os.path.join(OUT, "summary.csv"), index=False, float_format="%.6g", encoding="utf-8")
    S["對帳表"] = REC
    S["M4 換股統計"] = {"換股": int(ER["M4_換股"].sum()), "換股前已收復": int(ER["換股前已收復"].sum()),
                     "換股買不到": int((ER.get("M4_狀態", pd.Series(dtype=str)) == "換股買不到、續抱 0050").sum())}
    S["情報線整籃版（只並列）"] = INTEL
    S["結束（台北）"] = now_tpe(); S["耗時秒"] = round(time.time() - T0)
    json.dump(S, open(os.path.join(OUT, "G2.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    log("[彙總]\n" + SU[SU["段"] == "2015～（18 事件）"][["臂", "平均", "中位數", "勝率", "最差報酬", "最低帳面_最差（最大跌幅）", "平均持有天數"]].to_string())
    log(f"[M4] {S['M4 換股統計']}")
    log(f"[完] {S['耗時秒']}s")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--procs", type=int, default=3)
    a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    from backtest import researchAddOn as RA
    log = RA.log_to(os.path.join(OUT, "run.log"))
    run(a, log)


if __name__ == "__main__":
    main()

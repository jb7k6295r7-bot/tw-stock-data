# -*- coding: utf-8 -*-
"""USREG-A2-M／U／X（事件層）：USREG-M、U、X 在 S&P 500＋400 新母體重跑；三欄＝只 S&P 400／合併／只 S&P 500。

    PYTHONPATH=$HOME/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchUSA2 --m [--procs 2]
    PYTHONPATH=$HOME/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchUSA2 --u [--procs 2]
    PYTHONPATH=$HOME/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchUSA2 --x [--procs 2]

判準：USREG-A2 seq1（sha 8be74b36592db3f4；台北 2026-10-07 06:19）＋ 裁定 seq316（發號；判定口徑事先定死）；
     正文沿用 USREG seq2（a3c98a07e882a574）～seq5（ffb22ecb1bd749ff）＋裁定 seq214 §三 讀法（R1～R4、B1～B7）＋各件既有讀法（M U1～U13、U W1～W9、X V1～V12）。
既有程式（只 import、⛔ 一行未改；它們的 resultsUSM／U／X 不動）：researchUSM（prep、member_array、span_start_array）、researchUSM_body（Stk、low_aligned、ew_us、excl_mask）、
     researchM.summ／verdict、researchUSU（assign_us、merge_brk、ew_close_T）、researchU（dstat、dstat_agg、verdict、fake_positions、WD）、
     researchUSX（load_one、keep_A、keep_B、Mat、draw_ctl、judge、run_A、run_B、ew_close、outcome_B）、trendline_m、fib_u、patterns_x。
資料：backtest/researchUSA2_data.py（聯集轉接層，讀法 D1～D7；us-stock-data 881c86a9）。

⭐ 判定口徑（裁定 seq316，事先定死）：
   每格在「只 S&P 400」與「合併」各下一次結果（原登錄的出口／結果規則，一字不改）；
   合格 ＝ 兩者都「結果②（測得出（＋））」；只有合併過、S&P 400 單獨不過 ⇒「事後擴母體」（最多暫定、只進前瞻紀錄）；
   合併沒過 ⇒ 不合格（附合併的結果字樣）；只 S&P 500 ＝ 照舊描述（對 USREG-M／U／X 舊結果的重現，⛔ 不判）。
   每件結論句後附：「同一想法在 S&P 500 已測過一次」「S&P 400 整段缺價 48 檔不在母體 ⇒ 結果偏向存活股、偏樂觀」。

⭐ A2 改動（登錄 §一、§二）：
   窗 2016-01-04 ～ 2026-09-30；母體 ＝ 當天在 S&P 500 或 S&P 400（聯集實體，D1～D3）。
   M：判定 20 日（R_e ＝ px(T+21)／open(T+1) − 0.05%；X ＝ R_e −（EW_20(T+1) − 0.05%），基準 ＝ 合併母體）；描述 60／120／240 日（M 原描述臂 c 的式子推廣）。
   U：判定 20 日（D ＝ b(38.2,61.8) − 鄰位，±5% 帶、20 日窗）；描述 60／120／240 日窗（U 原描述臂 b「改窗」的式子推廣）。
   X：甲 H60 判、H120 描述（同一批事件 T ≤ 窗尾−120）、H240 描述（另一批：T ≤ 窗尾−240、未來窗斷點與對照可用改 240 日）；
      乙 20 日判；60／120／240 日描述（R_H ＝ close(≤S+H)／open(S+1) − 1 − 0.05% − EW_H(S+1)）。
   240 日：最多約 11 個 240 日區段 ⇒ 依構造只能出口①（登錄 §二 事前寫明）。

⭐ 執行者補讀法（登錄沒寫清楚 ⇒ 先寫死再算，台北 2026-10-07）：
 A1 三欄的事件歸屬 ＝ 事件日（M 的 T、U 的觸及日 T、X 的 T／S）當天屬哪個指數（資料轉接 D5）；合併窗、剔除、狀態都在聯集實體上算一次，三欄只是切開來看。
 A2 基準 ＝ 合併母體（登錄 §二「個股層基準：同母體（合併）」）；X 甲 對照抽自合併母體同日同十分位。
    敏感度（描述）：M、X 乙 的基準改成「該欄自己的指數成員」等權；X 甲 的對照改抽「該欄自己的指數」同日同十分位（十分位只在該指數成員內算）。
 A3 描述天數 H 的事件 ＝ 判定那批保留事件，再要求 T+1+H（X 乙：S+H）≤ 窗尾、且 [最早取點, T+1+H] 無硬斷點（M 原描述臂 c 同式）；
    區段長 ＝ H、區段上限 ＝ ⌊窗交易日 ÷ H⌋（M 原描述臂 c 同式）。U 的 H 日窗則照 U 原描述臂 b：每個 H 各自偵測、合併、斷點 [T, T+H]、T ≤ 窗尾−H；區段長 H。
 A4 假訊號臂：只跑各件的【判定用】那一版（M、X ＝ 新預設「只排除過去 20 日」30 次；U ＝ 登錄 §七 200 組隨機位置）；
    其餘描述版本（不排除、同檔同月、U 描述用假訊號臂）本批不重跑。假訊號依「抽中日當天在哪個指數」歸欄（A1 同規則）。
 A5 |ret|＞50% 敏感度（裁定 seq316；資料轉接 D6）：S&P 400 清單 23 列全未確認 ⇒ 主結果照用；
    敏感度 ＝ 事件的斷點範圍（M：[最早取點, T+21]；U：[T, T+H]；X 甲：[最早取點, T+120] 及對照股 (T, T+120]；X 乙：[最早取點, S+40]）
    碰到未確認列 ⇒ 剔除；M、X 乙 的基準另算「跨到未確認列的股票不進」版。
 A6 M 的描述臂 a～f、U 的 §五／§六 其餘描述、X 的描述細項（目標距離分佈、成形／破壞率等）本批不重跑（登錄只寫改動；主問題是判定格＋天數軸）。

⛔⛔ 授權：resultsUSA2/ 只放彙總（平均、CI、件數、比例、判語、sha）；逐筆事件寫 ~/us_work/a2/（repo 外）並列 sha。
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import os
import sys
import time
import zlib
from collections import Counter
from multiprocessing import Pool

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17"))
sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
from backtest import researchUSA2_data as A2
A2.install()
from backtest import us_data as U
from backtest import trendline_m as TM
from backtest import fib_u as FU
from backtest import patterns_x as PXD
from backtest import researchUSM as RU
from backtest import researchUSM_body as MB
from backtest import researchUSU as USU
from backtest import researchUSX as USX
from backtest import research11 as R11
import researchM as TWM
import researchU as TU

OUT = os.path.expanduser("~/tw-p17/backtest/resultsUSA2")
WORK = os.path.expanduser("~/us_work/a2")
COST = U.COST_ROUNDTRIP
SEED = 20260925
CAL0 = MB.CAL0
GROUPS = ("合併", "只S&P400", "只S&P500")
HDESC = (60, 120, 240)
REG = {"A2": "8be74b36592db3f4", "裁定": "seq316", "正文": "USREG seq2 a3c98a07e882a574 ～ seq5 ffb22ecb1bd749ff", "讀法": "seq214 §三"}
_G = {}


def sha256f(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def gmask(df, g):
    """A1：事件列 df 的 idx 欄（'400'／'500'）⇒ 該欄遮罩。"""
    if g == "合併":
        return np.ones(len(df), bool)
    return (df["idx"] == ("400" if g == "只S&P400" else "500")).to_numpy()


def passed(res):
    return isinstance(res, str) and res.startswith("結果②")


def a2_label(r_comb, r_400):
    """裁定 seq316：合格＝只 S&P 400 與合併都結果②；只有合併過 ⇒ 事後擴母體；合併沒過 ⇒ 不合格（附合併字樣）。"""
    if passed(r_comb) and passed(r_400):
        return "合格（兩個母體都測得出（＋））"
    if passed(r_comb):
        return "事後擴母體（合併測得出（＋）、只 S&P 400 沒有；最多暫定、只進前瞻紀錄）"
    tail = "；只 S&P 400 單獨測得出（＋）但合併沒有" if passed(r_400) else ""
    return "不合格（合併：{}{}）".format(r_comb, tail)


def setup_cal():
    calF = U.load_calendar(); cal = calF[calF >= CAL0]
    w0 = int(cal.searchsorted(A2.WINDOW[0])); w1 = int(cal.searchsorted(A2.WINDOW[1]))
    assert cal[w0] == A2.WINDOW[0] and cal[w1] == A2.WINDOW[1], (cal[w0], cal[w1])
    return cal, w0, w1


def tickers(lim=None):
    nos = set(A2.no_ohlc_tickers())
    t = [x for x in A2.tickers_all() if x not in nos]
    return t[:lim] if lim else t


def stock_common(t, cal, w0, wE):
    df = U.load_ohlc(t, scope="panel")
    if len(df) == 0:
        return None
    A = RU.prep(df, cal)
    if len(A["bars"]) == 0:
        return None
    S = MB.Stk(t, A, MB.low_aligned(df, cal), RU.member_array(t, cal), RU.span_start_array(t, cal), w0, wE)
    m5, m4 = A2.idx_member(t, cal)
    f50 = A2.flag50_pos(t, cal)
    return df, A, S, m5, m4, f50


def cs_of(b):
    return np.cumsum(b.astype(np.int64))


def hit(cs, a, b):
    return MB._cnt(cs, a, b) > 0


# ════════════════════════════════════ USREG-A2-M ════════════════════════════════════
M_METH = ("甲", "乙", "丙")
M_NAME = {"甲": "(甲) 兩點法", "乙": "(乙) 三點驗證法", "丙": "(丙) 回歸法"}
M_H = 21


def m_init(cal, w0, w1):
    _G.update(cal=cal, w0=w0, w1=w1)


def m_work(t):
    cal, w0, w1 = _G["cal"], _G["w0"], _G["w1"]; wE = w1 - M_H
    r = stock_common(t, cal, w0, wE)
    if r is None:
        return None
    df, A, S, m5, m4, f50 = r
    st = {}
    for m in M_METH:
        if m == "丙":
            rr = TM.detect_calendar(S.o, S.h, S.c, "丙", N=TM.REG_N, r2min=TM.REG_R2)
        else:
            rr = TM.detect_calendar(S.o, S.h, S.c, m, 5)
        st[m] = S.status([(e["T"], e["first"], None) for e in rr["events"]])
    return {"t": t, "S": S, "st": st, "m5": m5, "m4": m4, "f50": f50}


def run_m(procs, lim, reps):
    t0 = time.time()
    fx = {"A2資料轉接": A2.selftest(), "M本體UB1_UB6": MB.body_fixtures()}
    cal, w0, w1 = setup_cal(); n = len(cal); wE = w1 - M_H
    cap = -(-(wE - w0 + 1) // 20); _G["cap"] = cap
    tick = tickers(lim)
    print("[M] 資料 {}｜窗 {}～{}｜T ≤ {}｜區段上限 {}｜{} 檔".format(A2.data_commit()[:10], cal[w0].date(), cal[w1].date(), cal[wE].date(), cap, len(tick)), flush=True)
    with Pool(procs, initializer=m_init, initargs=(cal, w0, w1)) as pool:
        res = pool.map(m_work, tick, chunksize=4)
    ST = {r["t"]: r for r in res if r is not None}
    sids = sorted(ST); SS = {s: ST[s]["S"] for s in sids}
    print("[M] 可用 {} 檔｜{:.0f}s".format(len(sids), time.time() - t0), flush=True)
    O = np.column_stack([SS[s].o for s in sids]); okO = np.column_stack([SS[s].okO for s in sids])
    PXm = np.column_stack([SS[s].px for s in sids]); MEM = np.column_stack([SS[s].member for s in sids])
    M4 = np.column_stack([ST[s]["m4"] for s in sids]); M5 = np.column_stack([ST[s]["m5"] for s in sids])
    CSPB = np.column_stack([SS[s].cs_pb for s in sids])
    F50 = np.column_stack([ST[s]["f50"] for s in sids]); CSF = np.cumsum((F50 | np.column_stack([SS[s].pb for s in sids])).astype(np.int64), axis=0)
    okM = okO & MEM
    EW = {H: MB.ew_us(O, okM, PXm, CSPB, H) for H in (20,) + HDESC}
    EW_alt = MB.ew_us(O, okM, PXm, CSF, 20)
    EW_g = {"只S&P400": MB.ew_us(O, okO & M4, PXm, CSPB, 20), "只S&P500": MB.ew_us(O, okO & M5, PXm, CSPB, 20)}
    ew_n = okM[w0:wE + 2].sum(axis=1)
    del O, PXm
    print("[M] 基準 EW_20／60／120／240｜每日成分 中位 {:.0f}（{}～{}）｜{:.0f}s".format(np.median(ew_n), ew_n.min(), ew_n.max(), time.time() - t0), flush=True)
    wstart = np.datetime64(cal[w0])
    RES = {"性質": "USREG-A2-M（單筆層事件研究；判定三格 × 兩個母體；美股 N_前段 +3）", "登錄": REG, "資料commit": A2.data_commit(),
           "判定窗": [str(cal[w0].date()), str(cal[w1].date())], "T可落": [str(cal[w0].date()), str(cal[wE].date())], "可用檔數": len(sids),
           "區段上限_20日": int(cap), "基準每日成分數": {"中位": float(np.median(ew_n)), "最少": int(ew_n.min()), "最多": int(ew_n.max())},
           "fixture": fx, "格": {}}
    shas = []
    CSF1 = {s: np.cumsum(ST[s]["f50"]) for s in sids}
    CAND = {}
    for s in sids:
        S = SS[s]; c_ = np.arange(w0, wE + 1); CAND[s] = c_[S.member[w0:wE + 1] & S.valid[w0:wE + 1]]
    for mi, m in enumerate(M_METH):
        rows = []; acc = Counter()
        for s in sids:
            S = SS[s]; X = ST[s]
            for T, first, _, stt in X["st"][m]:
                gi = "400" if X["m4"][T] else "500"
                acc[(gi, stt)] += 1
                if stt != "保留":
                    continue
                g = S.px[T + M_H] / S.o[T + 1] - 1.0
                rows.append({"sid": s, "T": T, "first": first, "idx": gi, "g": g, "R": g - COST, "EW": EW[20][T + 1], "X": g - EW[20][T + 1],
                             "X_alt": g - EW_alt[T + 1], "X_own": g - EW_g["只S&P400" if gi == "400" else "只S&P500"][T + 1],
                             "f50": bool(MB._cnt(CSF1[s], first, T + M_H) > 0),
                             "grp": "期初已在" if S.spanst[T] <= wstart else "期中加入",
                             "退路": bool(S.fb[T + M_H]), "移出": bool((~S.member[T + 1:T + M_H + 1]).any())})
        E = pd.DataFrame(rows)
        cell = {}
        for g in GROUPS:
            e = E[gmask(E, g)]
            s_ = TWM.summ(e["X"], e["T"], cal, w0, cap=cap); ex, rs = TWM.verdict(s_) if s_["n"] else ("出口①", "—（無事件）")
            sR = TWM.summ(e["R"], e["T"], cal, w0, cap=cap)
            a = {k[1]: v for k, v in acc.items() if g == "合併" or k[0] == ("400" if g == "只S&P400" else "500")}
            if g == "合併":
                a = Counter()
                for k, v in acc.items():
                    a[k[1]] += v
            c = {**s_, "出口": ex, "結果": rs, "R_e平均": sR.get("平均"), "R_e中位": sR.get("中位"), "R>0": sR.get("勝率"),
                 "事件帳": {"母體內原始": int(sum(a.values())), **{k: int(a.get(k, 0)) for k in ("合併掉", "剔除_硬斷點", "剔除_T+1停牌", "保留")}},
                 "期初已在／期中加入": {"期初已在": int((e["grp"] == "期初已在").sum()), "期中加入": int((e["grp"] == "期中加入").sum())},
                 "出場用退路": int(e["退路"].sum()), "持有期內移出母體": int(e["移出"].sum())}
            ef = e[~e["f50"]]
            sf = TWM.summ(ef["X_alt"], ef["T"], cal, w0, cap=cap)
            c["敏感度_剔除未確認|ret|>50%列"] = {"剔除事件數": int(e["f50"].sum()), **{k: sf.get(k) for k in ("n", "平均", "lo", "hi", "n_eff")},
                                         "結果": (TWM.verdict(sf)[1] if sf["n"] else "—")}
            if g != "合併":
                so = TWM.summ(e["X_own"], e["T"], cal, w0, cap=cap)
                c["敏感度_基準改用該欄自己的指數等權"] = {k: so.get(k) for k in ("n", "平均", "lo", "hi", "n_eff")}
                c["敏感度_基準改用該欄自己的指數等權"]["結果"] = TWM.verdict(so)[1] if so["n"] else "—"
            # 描述天數（A3）
            for H in HDESC:
                xs, Ts, skip_w, skip_b = [], [], 0, 0
                capH = (w1 - w0 + 1) // H
                for ev in e.itertuples():
                    S = SS[ev.sid]; T = int(ev.T)
                    if T + 1 + H > w1:
                        skip_w += 1; continue
                    if S.brk(int(ev.first), T + 1 + H):
                        skip_b += 1; continue
                    xs.append(S.px[T + 1 + H] / S.o[T + 1] - 1.0 - EW[H][T + 1]); Ts.append(T)
                sH = TWM.summ(xs, Ts, cal, w0, blk=H, cap=capH)
                exH, rsH = TWM.verdict(sH) if sH["n"] else ("出口①", "—")
                c["描述_{}日".format(H)] = {**{k: sH.get(k) for k in ("n", "平均", "中位", "lo", "hi", "勝率", "區段數", "n_eff")}, "區段上限": int(capH),
                                          "出口": exH, "結果（描述、⛔ 不判）": rsH, "排除_超過窗尾": skip_w, "排除_延伸段硬斷點": skip_b,
                                          "依構造": "出口①（不可判定）" if capH < 30 else ("最好出口②" if capH < 100 else "出口③可能")}
            cell[g] = c
        cell["A2標籤"] = a2_label(cell["合併"]["結果"], cell["只S&P400"]["結果"])
        RES["格"][m] = cell
        p = os.path.join(WORK, "M_events_{}.csv".format(m))
        Eo = E.copy(); Eo.insert(1, "T_date", [str(cal[t].date()) for t in Eo["T"]]); Eo.to_csv(p, index=False)
        shas.append((os.path.basename(p), len(Eo), sha256f(p)))
        print("[M {}] {}".format(m, "｜".join("{} n {} X {:+.4f} [{:+.4f},{:+.4f}] {} {}".format(g, cell[g].get("n"), cell[g].get("平均", np.nan),
              cell[g].get("lo", np.nan), cell[g].get("hi", np.nan), cell[g]["出口"], cell[g]["結果"]) for g in GROUPS)), flush=True)
        print("     ⇒ {}".format(cell["A2標籤"]), flush=True)
        # 假訊號臂（A4：新預設、30 次）
        real = {s: np.sort(g_["T"].to_numpy()) for s, g_ in E.groupby("sid")}
        CANDX = {s: CAND[s][~MB.excl_mask(CAND[s], real[s])] for s in real}
        FK = []
        for r in range(reps):
            xs = {g: ([], []) for g in GROUPS}
            for s in sorted(real):
                S = SS[s]
                cand = CANDX[s]
                k = min(len(real[s]), len(cand))
                rng = np.random.default_rng([SEED + r, zlib.crc32(s.encode()), mi, 0])
                for T in np.sort(rng.choice(cand, size=k, replace=False)):
                    T = int(T)
                    if S.brk(T, T + M_H) or not S.valid[T + 1]:
                        continue
                    x = S.px[T + M_H] / S.o[T + 1] - 1.0 - EW[20][T + 1]
                    gi = "只S&P400" if ST[s]["m4"][T] else "只S&P500"
                    for g in ("合併", gi):
                        xs[g][0].append(x); xs[g][1].append(T)
            for g in GROUPS:
                sf = TWM.summ(xs[g][0], xs[g][1], cal, w0, cap=cap)
                pas = bool(sf["n"] and not (sf["lo"] <= 0 <= sf["hi"]))
                FK.append({"格": m, "欄": g, "r": r, "n": sf["n"], "平均X": sf.get("平均"), "lo": sf.get("lo"), "hi": sf.get("hi"),
                           "判過": pas, "判過_正": bool(pas and sf["平均"] > 0)})
        FK = pd.DataFrame(FK)
        for g in GROUPS:
            f = FK[FK["欄"] == g]
            fk = {"x／{}（CI不含0）".format(reps): int(f["判過"].sum()), "其中(+)": int(f["判過_正"].sum()), "平均X的平均": float(f["平均X"].mean()),
                  "平均保留數": float(f["n"].mean())}
            fk["警語"] = ("⚠ 假訊號也有 {}／{} 次測得出 ⇒ 結果句前加警語".format(fk["x／{}（CI不含0）".format(reps)], reps)
                        if (fk["x／{}（CI不含0）".format(reps)] >= 2 and passed(cell[g]["結果"])) else "（不加）")
            cell[g]["假訊號臂_新預設"] = fk
        FK.to_csv(os.path.join(OUT, "M_fake_arm_{}.csv".format(m)), index=False)
        print("[M {} 假訊號] {}｜{:.0f}s".format(m, {g: cell[g]["假訊號臂_新預設"]["x／{}（CI不含0）".format(reps)] for g in GROUPS}, time.time() - t0), flush=True)
    RES["先驗_只400效果量大於只500（只記錄）"] = {m: bool(abs(RES["格"][m]["只S&P400"].get("平均", 0)) > abs(RES["格"][m]["只S&P500"].get("平均", 0))) for m in M_METH}
    RES["先驗_標籤與S&P500時相同（只記錄）"] = "S&P 500 舊結果：三格測不出（resultsUSM）"
    RES["覆蓋_存活者偏差"] = A2.coverage(cal, w0, w1)
    RES["資料轉接計數"] = dict(A2.STATS)
    RES["逐筆檔sha（repo外）"] = {a: {"rows": b, "sha256": c} for a, b, c in shas}
    RES["耗時秒"] = round(time.time() - t0, 1)
    p = os.path.join(WORK, "M_ew.csv")
    pd.DataFrame({"date": [str(d.date()) for d in cal], **{"EW%d" % H: EW[H] for H in EW}, "EW20_alt": EW_alt,
                  "EW20_400": EW_g["只S&P400"], "EW20_500": EW_g["只S&P500"], "n_members": okM.sum(axis=1)}).to_csv(p, index=False)
    RES["逐筆檔sha（repo外）"]["M_ew.csv"] = {"rows": n, "sha256": sha256f(p)}
    json.dump(RES, open(os.path.join(OUT, "M_summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    print("[M] 完成 {:.0f}s".format(time.time() - t0), flush=True)


# ════════════════════════════════════ USREG-A2-U ════════════════════════════════════
U_H = (20,) + HDESC


def u_init(cal, w0, w1, fr, mon):
    _G.update(cal=cal, w0=w0, w1=w1, fr=fr, mon=mon)


def u_work(t):
    cal, w0, w1, fr, mon = _G["cal"], _G["w0"], _G["w1"], _G["fr"], _G["mon"]
    r = stock_common(t, cal, w0, w1 - 20)
    if r is None:
        return None
    df, A0, S, m5, m4, f50 = r
    h, l, c = S.h, S.l, S.c
    det = FU.detect_calendar(h, l, c, 5)
    csf = np.cumsum(f50)
    out = {"t": t, "E": {}}
    for H in U_H:
        rows, nonmem = USU.assign_us(S, det, w0, w1, H)
        E = pd.DataFrame(rows)
        if len(E):
            E["y"] = -9
            kp = (E["狀態"] == "保留").to_numpy(); T = E["T"].to_numpy(np.int64); p = E["p"].to_numpy(float)
            E.loc[kp, "y"] = FU.outcome_vec(c, T[kp], p[kp], H, FU.BAND)
            E["idx"] = np.where(m4[T], "400", "500")
            E["f50"] = [MB._cnt(csf, int(x), int(x) + H) > 0 for x in T]
            E["mon"] = [str(cal[x])[:7] for x in T]
            E["sid"] = t
        out["E"][H] = (E, nonmem)
    # 登錄假訊號臂（台股 B5；USU.work 同式），依抽中日的指數歸欄（A4）
    NM = mon.max() + 1
    acc = np.zeros((2, fr.shape[0] * fr.shape[1], NM, 2), np.int32)
    bars = det["bars"]; lb = l[bars]
    wb = [{"conf": W["conf_bar"], "end": W["end_bar"], "H0": W["H0"], "L0": W["L0"], "pre_min": W["pre_min"]} for W in det["waves"]]
    if wb:
        Tb, PP = FU.touches_many(wb, lb, fr.ravel())
        for j in range(Tb.shape[0]):
            ok = Tb[j] >= 0
            if not ok.any():
                continue
            Tc = bars[Tb[j][ok]]; pc = PP[j][ok]
            w_ = (Tc >= w0) & (Tc <= w1 - 20) & S.member[Tc] & S.valid[Tc]
            if not w_.any():
                continue
            Tc, pc = Tc[w_], pc[w_]
            o_ = np.argsort(Tc, kind="stable"); Tc, pc = Tc[o_], pc[o_]
            Tk, pk, _, _ = USU.merge_brk(S, Tc, pc)
            if len(Tk) == 0:
                continue
            y = FU.outcome_vec(c, Tk, pk); d_ = y >= 0
            gi = m4[Tk].astype(int)
            for gg in (0, 1):
                sel = d_ & (gi == gg)
                np.add.at(acc[gg, j, :, 0], mon[Tk[sel]], 1); np.add.at(acc[gg, j, :, 1], mon[Tk[sel]], y[sel].astype(np.int32))
    out["fake"] = acc
    return out


def neff_blk(E, w0, blk, cap, pos=FU.SIX):
    o = {}
    for p in pos:
        d = E[(E["pos"] == p) & (E["y"] >= 0)]
        nb = int(np.minimum((d["T"] - w0) // blk, cap - 1).nunique()) if len(d) else 0
        o[p] = {"分勝負事件": int(len(d)), "區段": nb, "min": int(min(len(d), nb))}
    return min(v["min"] for v in o.values()), min(v["分勝負事件"] for v in o.values()), o


def u_judge(E, w0, w1, H):
    wE = w1 - H
    blk = 20 if H == 20 else H
    cap = -(-(wE - w0 + 1) // 20) if H == 20 else (w1 - w0 + 1) // H
    if len(E) == 0 or (E["y"] >= 0).sum() == 0:
        return {"n": 0, "出口": "出口①", "結果": "—（無事件）"}
    sm = TU.dstat(E, TU.WD, "mon")
    ne, nmin, ned = neff_blk(E, w0, blk, cap)
    ex, rs = TU.verdict(sm, ne, nmin) if np.isfinite(sm["D"]) else ("出口①", "—（有位置 0 筆）")
    und = {p: {"分勝負": int(((E["pos"] == p) & (E["y"] >= 0)).sum()), "反彈": int(((E["pos"] == p) & (E["y"] == 1)).sum())} for p in FU.POS}
    for p in und:
        und[p]["b"] = und[p]["反彈"] / max(1, und[p]["分勝負"])
    return {"D": sm["D"], "lo": sm["lo"], "hi": sm["hi"], "se": sm["se"], "曆月數": sm.get("群數"), "n_eff": ne, "n分勝負最少位置": nmin,
            "區段長": blk, "區段上限": int(cap), "出口": ex, "結果": rs, "各位置": und, "保留": int(len(E))}


def run_u(procs, lim, reps):
    t0 = time.time()
    fx = {"A2資料轉接": A2.selftest(), "台股本體自測G1_G4": TU.selftest(), "美股UU1_UU2": USU.usu_fixtures()}
    cal, w0, w1 = setup_cal(); n = len(cal)
    base = cal[w0].year * 12 + cal[w0].month
    mon = np.clip(np.array([d.year * 12 + d.month - base for d in cal]), 0, None)
    fr, ab = TU.fake_positions(reps)
    tick = tickers(lim)
    print("[U] 資料 {}｜窗 {}～{}｜{} 檔".format(A2.data_commit()[:10], cal[w0].date(), cal[w1].date(), len(tick)), flush=True)
    NM = int(mon.max() + 1)
    FR = np.zeros((2, reps * 6, NM, 2), np.int64)
    Es = {H: [] for H in U_H}; nonmem = Counter()
    with Pool(procs, initializer=u_init, initargs=(cal, w0, w1, fr, mon)) as pool:
        for r in pool.imap_unordered(u_work, tick, chunksize=4):
            if r is None:
                continue
            FR += r["fake"]
            for H in U_H:
                E, nm = r["E"][H]
                nonmem[H] += nm
                if len(E):
                    Es[H].append(E)
    print("[U] 讀檔＋偵測 {:.0f}s".format(time.time() - t0), flush=True)
    RES = {"性質": "USREG-A2-U（單筆層；判定一格 × 兩個母體；美股 N_前段 +1）", "登錄": REG, "資料commit": A2.data_commit(),
           "判定窗": [str(cal[w0].date()), str(cal[w1].date())], "fixture": fx, "天數": {}}
    shas = []
    for H in U_H:
        EA = pd.concat(Es[H], ignore_index=True)
        acc = EA.groupby(["idx", "狀態"]).size().to_dict()
        K = EA[EA["狀態"] == "保留"].copy()
        out = {}
        for g in GROUPS:
            e = K[gmask(K, g)]
            j = u_judge(e, w0, w1, H)
            ea = EA[gmask(EA, g)]
            j["事件帳"] = {s_: int((ea["狀態"] == s_).sum()) for s_ in ("保留", "合併掉", "剔除_硬斷點")}
            jf = u_judge(e[~e["f50"]], w0, w1, H)
            j["敏感度_剔除未確認|ret|>50%列"] = {"剔除事件數": int(e["f50"].sum()), "D": jf.get("D"), "lo": jf.get("lo"), "hi": jf.get("hi"), "結果": jf["結果"]}
            if H == 20:
                fk = []
                for r in range(reps):
                    Dv_s = []
                    for gg in ((0, 1) if g == "合併" else ((1,) if g == "只S&P400" else (0,))):
                        Dv_s.append(FR[gg, r * 6:(r + 1) * 6])
                    Aa = sum(Dv_s)
                    Dv, se, b, nx = TU.dstat_agg(Aa, [(1, 0.5), (0, -0.25), (2, -0.25), (4, 0.5), (3, -0.25), (5, -0.25)])
                    fk.append(Dv)
                fD = np.array(fk, float); p95 = float(np.nanpercentile(fD, 95))
                xge = int(np.nansum(fD >= j["D"])) if np.isfinite(j.get("D", np.nan)) else None
                j["假訊號臂_登錄200組"] = {"次數": reps, "真D百分位": float(np.nanmean(fD < j["D"]) * 100) if xge is not None else None,
                                     "D_fake≥真D次數": xge, "D_fake的95百分位": p95, "D_fake平均": float(np.nanmean(fD)),
                                     "警語": ("⚠ 隨機兩個位置也有 {}／{} 同樣好".format(xge, reps) if (passed(j["結果"]) and j["D"] <= p95) else "（不加）")}
            j["描述或判定"] = "判定" if H == 20 else "描述（⛔ 不判）"
            if H == 240:
                j["依構造"] = "240 日區段最多 {} 段 ⇒ 出口①（不可判定）".format(j.get("區段上限"))
            out[g] = j
        if H == 20:
            out["A2標籤"] = a2_label(out["合併"]["結果"], out["只S&P400"]["結果"])
        out["不在母體的觸及（不開窗）"] = int(nonmem[H])
        RES["天數"][str(H)] = out
        p = os.path.join(WORK, "U_events_H{}.csv.gz".format(H))
        Ko = K.drop(columns=[c for c in ("L0", "H0") if c in K]).copy(); Ko["T_date"] = [str(cal[x].date()) for x in Ko["T"]]; Ko.to_csv(p, index=False)
        shas.append((os.path.basename(p), len(Ko), sha256f(p)))
        print("[U H{}] {}".format(H, "｜".join("{} D {:+.4f} [{:+.4f},{:+.4f}] n_eff {} {} {}".format(g, out[g].get("D", np.nan), out[g].get("lo", np.nan),
              out[g].get("hi", np.nan), out[g].get("n_eff"), out[g]["出口"], out[g]["結果"]) for g in GROUPS)), flush=True)
    print("     ⇒ {}".format(RES["天數"]["20"]["A2標籤"]), flush=True)
    j4, j5 = RES["天數"]["20"]["只S&P400"], RES["天數"]["20"]["只S&P500"]
    RES["先驗_只400效果量大於只500（只記錄）"] = bool(abs(j4.get("D", 0)) > abs(j5.get("D", 0)))
    RES["先驗_標籤與S&P500時相同（只記錄）"] = "S&P 500 舊結果：測不出（resultsUSU）"
    RES["覆蓋_存活者偏差"] = A2.coverage(cal, w0, w1)
    RES["逐筆檔sha（repo外）"] = {a: {"rows": b, "sha256": c} for a, b, c in shas}
    RES["耗時秒"] = round(time.time() - t0, 1)
    json.dump(RES, open(os.path.join(OUT, "U_summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    print("[U] 完成 {:.0f}s".format(time.time() - t0), flush=True)


# ════════════════════════════════════ USREG-A2-X ════════════════════════════════════
def x_init(cal, w0, w1):
    USX._init(cal, w0, w1); _G.update(cal=cal, w0=w0, w1=w1)


def x_work(t):
    r = USX.load_one(t)
    if r is None:
        return None
    cal = _G["cal"]
    m5, m4 = A2.idx_member(t, cal)
    r["m4"] = m4; r["m5"] = m5; r["f50"] = A2.flag50_pos(t, cal)
    return r


def run_A_H(ST, M, cal, w0, keptA, Hs, hmax):
    """USX.run_A 同式（同一條亂數流 default_rng(20260925)、事件依 (T, 代號) 排序、每事件抽 1 檔對照），但 H 與未來窗長度可給（A2 的 H240 批）。"""
    out = {}
    for typ in PXD.TYPES_A:
        rng = np.random.default_rng(USX.SEED)
        evs = sorted([dict(e, sid=s) for s in keptA[typ] for e in keptA[typ][s]], key=lambda e: (e["T"], e["sid"]))
        rows = []
        for e in evs:
            i = M.ix[e["sid"]]; T = e["T"]
            j, psz, pk = USX.draw_ctl(M, i, T, rng)
            if j is None:
                continue
            tgt_c = M.C[j, T] * (1.0 + e["dist"])
            r = {"sid": e["sid"], "t": T, "month": cal[T].strftime("%Y-%m"), "first": e["first"], "ctl": M.sids[j], "dist": e["dist"]}
            for H in Hs:
                r[f"sig_{H}"] = M.hit(i, T, H, e["target"]); r[f"ctl_{H}"] = M.hit(j, T, H, tgt_c); r[f"d_{H}"] = r[f"sig_{H}"] - r[f"ctl_{H}"]
            rows.append(r)
        out[typ] = pd.DataFrame(rows, columns=["sid", "t", "month", "first", "ctl", "dist"] + [f"{k}_{H}" for H in Hs for k in ("sig", "ctl", "d")]) if not rows else pd.DataFrame(rows)
    return out


def x_tag(X, ST, key="t"):
    X = X.copy()
    if len(X) == 0:
        X["idx"] = []
        return X
    X["idx"] = ["400" if ST[s]["m4"][t] else "500" for s, t in zip(X["sid"], X[key])]
    return X


def x_cell_judge(X, cal, w0, H, col_d=None, hitcols=None, col="d"):
    if col_d is not None:
        X = X.assign(d=X[col_d])
    if len(X) == 0:
        return {"n": 0, "出口": "出口①", "結果": "—（無事件）"}
    return USX.judge(X, cal, w0, H, col=col, hitcols=hitcols)


def run_x(procs, lim, reps):
    t0 = time.time()
    from backtest import selftest_patterns_x as STX
    t1, _ = STX.run_all()
    bad = [k for k, v in t1.items() if not v]
    if bad:
        raise SystemExit("⛔ T1 不過：{}".format(bad))
    fx = {"A2資料轉接": A2.selftest(), "T1台股合成型態": t1}
    cal, w0, w1 = setup_cal(); n = len(cal)
    tick = tickers(lim)
    with Pool(procs, initializer=x_init, initargs=(cal, w0, w1)) as pool:
        res = pool.map(x_work, tick, chunksize=4)
    ST = {r["t"]: r for r in res if r is not None}
    USX._G.update(cal=cal, w0=w0, w1=w1)
    sids = sorted(ST)
    print("[X] 資料 {}｜可用 {} 檔｜窗 {}～{}｜{:.0f}s".format(A2.data_commit()[:10], len(sids), cal[w0].date(), cal[w1].date(), time.time() - t0), flush=True)
    rs = np.random.default_rng(20260927)
    fx["美股UX1_UX3"] = USX.usx_fixtures([str(x) for x in rs.choice(sids, 8, replace=False)])
    wE, wB, wE240 = w1 - USX.HMAX, w1 - USX.FORM_N, w1 - 240
    keptA = {typ: {} for typ in PXD.TYPES_A}; keptB = {typ: {} for typ in PXD.TYPES_B}; keptA240 = {typ: {} for typ in PXD.TYPES_A}
    accA = {typ: Counter() for typ in PXD.TYPES_A}; accB = {typ: Counter() for typ in PXD.TYPES_B}
    for s in sids:
        for typ in PXD.TYPES_A:
            k, a = USX.keep_A(ST[s], typ, w0, wE, n)
            accA[typ].update(a)
            if k:
                keptA[typ][s] = k
            k2, _ = USX.keep_A(ST[s], typ, w0, wE240, n, hz=240)
            if k2:
                keptA240[typ][s] = k2
        for typ in PXD.TYPES_B:
            k, a = USX.keep_B(ST[s], typ, w0, wB, n)
            accB[typ].update(a)
            if k:
                keptB[typ][s] = k
    SS = [ST[s]["S"] for s in sids]
    O = np.column_stack([x.o for x in SS]); okO = np.column_stack([x.okO for x in SS]); MEMc = np.column_stack([x.member for x in SS])
    M4 = np.column_stack([ST[s]["m4"] for s in sids]); M5 = np.column_stack([ST[s]["m5"] for s in sids])
    CFF = np.column_stack([ST[s]["cff"] for s in sids]); CSPB = np.column_stack([x.cs_pb for x in SS])
    F50 = np.column_stack([ST[s]["f50"] for s in sids]); CSF = np.cumsum((F50 | np.column_stack([x.pb for x in SS])).astype(np.int64), axis=0)
    okM = okO & MEMc
    EW = {H: USX.ew_close(O, okM, CFF, CSPB, H) for H in (20,) + HDESC}
    EW_alt = USX.ew_close(O, okM, CFF, CSF, 20)
    EW_g = {"只S&P400": USX.ew_close(O, okO & M4, CFF, CSPB, 20), "只S&P500": USX.ew_close(O, okO & M5, CFF, CSPB, 20)}
    del O, CFF
    M = USX.Mat(ST, n, w0, wE, wB)
    print("[X] 橫斷面｜{:.0f}s".format(time.time() - t0), flush=True)
    rowsA = run_A_H(ST, M, cal, w0, keptA, (60, 120), 120)
    # H240 批（A2 新增描述）：未來窗斷點與對照可用改 240 日
    M240 = USX.Mat.__new__(USX.Mat); M240.__dict__.update(M.__dict__); M240._pool = {}
    OK240 = np.zeros_like(M.OK)
    for s in sids:
        S = ST[s]["S"]; i = M.ix[s]; t = np.arange(1, n - 240 - 1)
        brk = ((S.cs_pb[t + 240] - S.cs_pb[t]) > 0) | ((S.cs_ms[t + 240] - S.cs_ms[t]) > 0)
        OK240[i, t] = S.valid[t] & S.member[t] & S.valid[t + 1] & ~brk
    M240.OK = OK240
    rowsA240 = run_A_H(ST, M240, cal, w0, keptA240, (240,), 240)
    _tb = USX.TB; USX.TB = tuple(t_ for t_ in PXD.TYPES_B if keptB[t_])
    try:
        resB, rowsB = USX.run_B(ST, cal, w0, wB, n, EW[20], keptB)
    finally:
        USX.TB = _tb
    for t_ in PXD.TYPES_B:
        rowsB.setdefault(t_, pd.DataFrame(columns=["sid", "t", "month", "R", "EW", "X"]))
    print("[X] 甲乙主體｜{:.0f}s".format(time.time() - t0), flush=True)
    RES = {"性質": "USREG-A2-X（單筆層；甲 5＋乙 6 × 兩個母體；美股 N_前段 +11）", "登錄": REG, "資料commit": A2.data_commit(),
           "判定窗": [str(cal[w0].date()), str(cal[w1].date())], "甲T可落": str(cal[wE].date()), "甲H240批T可落": str(cal[wE240].date()),
           "乙S可落": str(cal[wB].date()), "可用檔數": len(sids), "fixture": fx, "開跑前算術": USX.arith(cal, w0, w1), "甲": {}, "乙": {}}
    RES["開跑前算術"]["甲_H240（A2 新增）"] = {"可用日": int(wE240 - w0 + 1), "最多區段": int(-(-(wE240 - w0 + 1) // 240)), "依構造": "出口①（不可判定）"}
    shas = []
    cs_f = {s: np.cumsum(ST[s]["f50"]) for s in sids}
    for typ in PXD.TYPES_A:
        X = x_tag(rowsA[typ], ST); X240 = x_tag(rowsA240[typ], ST)
        if len(X):
            X["f50"] = [MB._cnt(cs_f[s], int(f), int(t) + 120) > 0 or MB._cnt(cs_f[c], int(t) + 1, int(t) + 120) > 0
                        for s, f, t, c in zip(X["sid"], X["first"], X["t"], X["ctl"])]
        cell = {}
        for g in GROUPS:
            e = X[gmask(X, g)] if len(X) else X
            j60 = x_cell_judge(e, cal, w0, 60, col_d="d_60", hitcols=("sig_60", "ctl_60"))
            j120 = x_cell_judge(e, cal, w0, 120, col_d="d_120", hitcols=("sig_120", "ctl_120"))
            e240 = X240[gmask(X240, g)] if len(X240) else X240
            j240 = x_cell_judge(e240, cal, w0, 240, col_d="d_240", hitcols=("sig_240", "ctl_240"))
            ef = e[~e["f50"]] if len(e) else e
            jf = x_cell_judge(ef, cal, w0, 60, col_d="d_60", hitcols=("sig_60", "ctl_60"))
            res_ = j60["結果"] if j60["出口"] != "出口①" else "—（出口①：樣本不足以分辨）"
            cell[g] = {"H60（判定）": j60, "H120（描述：依構造不可判定）": j120, "H240（描述：依構造不可判定）": j240, "格的結果": res_,
                       "敏感度_剔除未確認|ret|>50%列": {"剔除事件數": int(e["f50"].sum()) if len(e) else 0, "D": jf.get("D"), "lo": jf.get("lo"),
                                               "hi": jf.get("hi"), "結果": jf["結果"]}}
        cell["A2標籤"] = a2_label(cell["合併"]["格的結果"], cell["只S&P400"]["格的結果"])
        cell["帳（合併）"] = dict(accA[typ])
        RES["甲"][typ] = cell
        for nm_, XX in (("A", X), ("A240", X240)):
            p = os.path.join(WORK, f"X_{nm_}_{typ}.csv.gz"); XX.to_csv(p, index=False); shas.append((os.path.basename(p), len(XX), sha256f(p)))
        print("[X 甲 {}] {} ⇒ {}".format(USX.NAME[typ], "｜".join("{} n {} D {:+.4f} {}".format(g, cell[g]["H60（判定）"].get("n"), cell[g]["H60（判定）"].get("D", np.nan),
              cell[g]["格的結果"]) for g in GROUPS), cell["A2標籤"]), flush=True)
    # 敏感度（描述）：甲 的對照改抽「該欄自己的指數」同日同十分位（十分位也只在該指數成員內算）
    VOL = np.vstack([ST[s]["vol"] for s in sids]); MEMV = np.vstack([x.member & x.valid for x in SS])
    G4 = np.vstack([ST[s]["m4"] for s in sids]); G5 = np.vstack([ST[s]["m5"] for s in sids])
    for g, GM, code in (("只S&P400", G4, True), ("只S&P500", G5, False)):
        Mg = USX.Mat.__new__(USX.Mat); Mg.__dict__.update(M.__dict__); Mg._pool = {}
        DEC = np.full_like(M.DEC, -1)
        for t in range(w0, max(wE, wB) + 1):
            v = VOL[:, t]; ok = np.flatnonzero(np.isfinite(v) & MEMV[:, t] & GM[:, t])
            if len(ok) == 0:
                continue
            order = ok[np.lexsort((ok, v[ok]))]
            DEC[order, t] = (np.arange(len(order)) * 10) // len(order)
        Mg.DEC = DEC
        kg = {typ: {s: [e for e in keptA[typ][s] if bool(ST[s]["m4"][e["T"]]) == code] for s in keptA[typ]} for typ in PXD.TYPES_A}
        kg = {typ: {s: v for s, v in d.items() if v} for typ, d in kg.items()}
        rg = run_A_H(ST, Mg, cal, w0, kg, (60,), 120)
        for typ in PXD.TYPES_A:
            jg = x_cell_judge(rg[typ], cal, w0, 60, col_d="d_60", hitcols=("sig_60", "ctl_60")) if len(rg[typ]) else {"n": 0, "結果": "—"}
            RES["甲"][typ][g]["敏感度_對照改抽該欄自己的指數"] = {k: jg.get(k) for k in ("n", "D", "lo", "hi", "n_eff", "事件達成率", "對照達成率", "出口", "結果")}
        print("[X 甲 對照改抽{}] {}".format(g, {typ: (RES["甲"][typ][g]["敏感度_對照改抽該欄自己的指數"].get("D"), RES["甲"][typ][g]["敏感度_對照改抽該欄自己的指數"]["結果"]) for typ in PXD.TYPES_A}), flush=True)
    del VOL, MEMV, G4, G5
    for typ in PXD.TYPES_B:
        X = x_tag(rowsB[typ], ST)
        if len(X):
            X["X_alt"] = X["R"] - COST - np.array([EW_alt[t + 1] for t in X["t"]])
            X["X_own"] = X["R"] - COST - np.array([EW_g["只S&P400" if i == "400" else "只S&P500"][t + 1] for t, i in zip(X["t"], X["idx"])])
            fst = {(s, g_["S"]): g_["first"] for s in keptB[typ] for g_ in keptB[typ][s]}
            X["f50"] = [MB._cnt(cs_f[s], int(fst[(s, t)]), int(t) + USX.FORM_N) > 0 for s, t in zip(X["sid"], X["t"])]
            for H in HDESC:
                v = []
                for s, t, f in zip(X["sid"], X["t"], X["f50"]):
                    S = ST[s]["S"]
                    if t + H > w1 or S.brk(t + 1, t + H):
                        v.append(np.nan); continue
                    v.append(ST[s]["cff"][t + H] / S.o[t + 1] - 1.0 - COST - EW[H][t + 1])
                X[f"X_{H}"] = v
        cell = {}
        for g in GROUPS:
            e = X[gmask(X, g)] if len(X) else X
            j = x_cell_judge(e, cal, w0, USX.EX_N, col="X")
            c = {"20日（判定）": j, "格的結果": j["結果"]}
            for H in HDESC:
                eh = e[np.isfinite(e[f"X_{H}"])] if len(e) else e
                jh = x_cell_judge(eh, cal, w0, H, col=f"X_{H}") if len(eh) else {"n": 0, "結果": "—"}
                capH = (w1 - w0 + 1) // H
                c[f"{H}日（描述、⛔ 不判）"] = {**{k: jh.get(k) for k in ("n", "D", "lo", "hi", "區段數", "n_eff", "出口", "結果")}, "區段上限": int(capH)}
            ef = e[~e["f50"]] if len(e) else e
            jf = x_cell_judge(ef, cal, w0, USX.EX_N, col="X_alt") if len(ef) else {"結果": "—"}
            c["敏感度_剔除未確認|ret|>50%列"] = {"剔除事件數": int(e["f50"].sum()) if len(e) else 0, **{k: jf.get(k) for k in ("n", "D", "lo", "hi", "結果")}}
            if g != "合併" and len(e):
                jo = x_cell_judge(e, cal, w0, USX.EX_N, col="X_own")
                c["敏感度_基準改用該欄自己的指數等權"] = {k: jo.get(k) for k in ("n", "D", "lo", "hi", "結果")}
            cell[g] = c
        cell["A2標籤"] = a2_label(cell["合併"]["格的結果"], cell["只S&P400"]["格的結果"])
        cell["帳（合併）"] = dict(accB[typ])
        RES["乙"][typ] = cell
        p = os.path.join(WORK, f"X_B_{typ}.csv.gz"); X.to_csv(p, index=False); shas.append((os.path.basename(p), len(X), sha256f(p)))
        print("[X 乙 {}] {} ⇒ {}".format(USX.NAME[typ], "｜".join("{} n {} X {:+.4f} {}".format(g, cell[g]["20日（判定）"].get("n"), cell[g]["20日（判定）"].get("D", np.nan),
              cell[g]["格的結果"]) for g in GROUPS), cell["A2標籤"]), flush=True)
    # 假訊號臂（A4：新預設 30 次；甲 只 H60、乙 20 日）
    FK = x_fake(ST, M, cal, w0, wE, wB, EW[20], rowsA, rowsB, reps)
    FK.to_csv(os.path.join(OUT, "X_fake_arm.csv"), index=False)
    for (tag, typ, g), f in FK.groupby(["tag", "typ", "欄"]):
        d = RES[tag][typ][g]
        x = int(f["判過"].sum())
        d["假訊號臂_新預設"] = {"x／{}（CI不含0）".format(reps): x, "其中(+)": int(f["判過_正"].sum()), "平均D": float(f["D"].mean())}
        d["假訊號臂_新預設"]["警語"] = ("⚠ 假訊號也有 {}／{} 次測得出 ⇒ 結果句前加警語".format(x, reps) if (x >= 2 and passed(d["格的結果"])) else "（不加）")
    RES["先驗_只400效果量大於只500（只記錄）"] = {
        **{"甲_" + t_: bool(abs(RES["甲"][t_]["只S&P400"]["H60（判定）"].get("D", 0) or 0) > abs(RES["甲"][t_]["只S&P500"]["H60（判定）"].get("D", 0) or 0)) for t_ in PXD.TYPES_A},
        **{"乙_" + t_: bool(abs(RES["乙"][t_]["只S&P400"]["20日（判定）"].get("D", 0) or 0) > abs(RES["乙"][t_]["只S&P500"]["20日（判定）"].get("D", 0) or 0)) for t_ in PXD.TYPES_B}}
    RES["先驗_標籤與S&P500時相同（只記錄）"] = "S&P 500 舊結果：11 格中 9 格測不出、乙 箱型兩格小幅負（resultsUSX）"
    RES["覆蓋_存活者偏差"] = A2.coverage(cal, w0, w1)
    RES["逐筆檔sha（repo外）"] = {a: {"rows": b, "sha256": c} for a, b, c in shas}
    RES["耗時秒"] = round(time.time() - t0, 1)
    json.dump(RES, open(os.path.join(OUT, "X_summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    print("[X] 完成 {:.0f}s".format(time.time() - t0), flush=True)


_KF = {}


def keptA_first(keptA, typ, s, t):
    k = (typ, s)
    if k not in _KF:
        _KF[k] = {e["T"]: e["first"] for e in keptA[typ].get(s, [])}
    return _KF[k][t]


def x_fake(ST, M, cal, w0, wE, wB, EW, rowsA, rowsB, reps):
    """USX.run_fake 的新預設版（vi＝0、同一套種子 [20260925＋r, crc32(代號), 型序號(乙＋10), 0]），每筆依抽中日的指數歸欄。"""
    out = []
    mon = np.array([cal[t].strftime("%Y-%m") for t in range(len(cal))])
    for tag, types, rowsX, OKM, end in (("甲", PXD.TYPES_A, rowsA, M.OK, wE), ("乙", PXD.TYPES_B, rowsB, M.OK40, wB)):
        for ti, typ in enumerate(types):
            X = rowsX[typ]
            if len(X) == 0:
                continue
            real = {s: g.sort_values("t") for s, g in X.groupby("sid")}
            cand = {}
            for s, g in real.items():
                i = M.ix[s]; idx = np.arange(w0, end + 1)
                ok = OKM[i, w0:end + 1] & ((M.DEC[i, w0:end + 1] >= 0) if tag == "甲" else True)
                c = idx[ok]; cand[s] = c[~MB.excl_mask(c, g["t"].to_numpy())]
            for r in range(reps):
                rows = []
                for s in sorted(real):
                    g = real[s]; i = M.ix[s]
                    rng = np.random.default_rng([USX.SEED + r, zlib.crc32(s.encode()), ti + (0 if tag == "甲" else 10), 0])
                    k = min(len(g), len(cand[s]))
                    days = list(np.sort(rng.choice(cand[s], size=k, replace=False))) if k else []
                    dists = list(g["dist"].to_numpy()[:k]) if tag == "甲" else []
                    for q, t in enumerate(days):
                        t = int(t); gi = "400" if ST[s]["m4"][t] else "500"
                        if tag == "甲":
                            j, _, _ = USX.draw_ctl(M, i, t, rng)
                            if j is None:
                                continue
                            dist = dists[q]
                            sg = M.hit(i, t, 60, M.C[i, t] * (1 + dist)); ct = M.hit(j, t, 60, M.C[j, t] * (1 + dist))
                            rows.append({"t": t, "month": mon[t], "idx": gi, "d": sg - ct, "sig_60": sg, "ctl_60": ct})
                        else:
                            S = ST[s]["S"]
                            rows.append({"t": t, "month": mon[t], "idx": gi, "X": ST[s]["cff"][t + USX.EX_N] / S.o[t + 1] - 1.0 - COST - EW[t + 1]})
                F = pd.DataFrame(rows)
                for g in GROUPS:
                    e = F[gmask(F, g)] if len(F) else F
                    if tag == "甲":
                        jf = x_cell_judge(e, cal, w0, 60, hitcols=("sig_60", "ctl_60")) if len(e) else {"n": 0}
                    else:
                        jf = x_cell_judge(e, cal, w0, USX.EX_N, col="X") if len(e) else {"n": 0}
                    pas = bool(jf.get("n", 0) and np.isfinite(jf.get("lo", np.nan)) and not (jf["lo"] <= 0 <= jf["hi"]))
                    out.append({"tag": tag, "typ": typ, "欄": g, "r": r, "n": jf.get("n"), "D": jf.get("D"), "lo": jf.get("lo"), "hi": jf.get("hi"),
                                "判過": pas, "判過_正": bool(pas and jf["D"] > 0)})
            print("[X 假訊號] {} {} 完成".format(tag, USX.NAME[typ]), flush=True)
    return pd.DataFrame(out)


def main():
    procs = int(sys.argv[sys.argv.index("--procs") + 1]) if "--procs" in sys.argv else 2
    lim = int(sys.argv[sys.argv.index("--limit") + 1]) if "--limit" in sys.argv else None
    os.makedirs(OUT, exist_ok=True); os.makedirs(WORK, exist_ok=True)
    if "--m" in sys.argv:
        run_m(procs, lim, int(sys.argv[sys.argv.index("--reps") + 1]) if "--reps" in sys.argv else 30)
    if "--u" in sys.argv:
        run_u(procs, lim, int(sys.argv[sys.argv.index("--reps") + 1]) if "--reps" in sys.argv else 200)
    if "--x" in sys.argv:
        run_x(procs, lim, int(sys.argv[sys.argv.index("--reps") + 1]) if "--reps" in sys.argv else 30)


if __name__ == "__main__":
    main()

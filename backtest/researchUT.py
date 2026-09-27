# -*- coding: utf-8 -*-
"""PREREG上升趨勢線（上升趨勢線被跌破：三畫法 × R∈{3,5,10} × 跌破判準 {1% 穿越, 3 日 3%}，18 格全報；主格 甲×R5×1% 唯一判定）
——pre（頻率、可判定性）＋本體。判準＝台股策略線 登錄 seq1（sha ffac12dee65c6bf1，2026-09-27 12:38）；裁定 seq225、seq226（發號、N_前段 ＋1）。

    python -m backtest.researchUT pre     ⇒ 只數事件、剔除、區段、出口（⛔ 不讀 T+1 以後任何價格）
    python -m backtest.researchUT body    ⇒ 本體（主格判定＋17 格描述＋控制組＋放棄組＋假訊號臂＋60 日＋分年／上市上櫃）
    選項 --limit N（除錯）；⛔ 單一行程（協調者：最多 1 個行程）

資料、母體、讀檔、硬斷點、漲跌停：與 PREREGM 同一份快照與同一套函式（import researchH2：main edc6f8002f、gate3、H2.brk、tradability、delist on）。
偵測器：backtest/trendline_ut.py（trendline_m 的鏡像；fixture backtest/selftest_trendline_ut.py，開跑前先全跑）。
量（登錄 §二「同 PREREGM」）：R_e ＝ px(T+21)／還原 open(T+1) − 1 − 0.585%；X_e ＝ R_e −（EW_20(T+1) − 0.585%）；EW ＝ researchM.ew_open（gate3 等權）。

⭐ 讀法（PREREGM 的 Q1～Q8、B1～B15 逐條鏡像；⛔ 看任何報酬前寫死；★ ＝ 新的兩種讀法、兩邊都數）：
 V1 窗 [2017-03-02, 2026-08-24]；T ∈ [窗首, 窗尾−21]；T 是有效 K 棒；T+1、T+21、合併 20 日、20 日區段（上限 115）用交易日曆。
 V2 狀態順序（Q2）：同檔同格依時間走 ⇒ (t0, t0+20] 內 ⇒ 合併掉；否則 硬斷點 [最早取點（丙：回歸窗起點）, T+21] → T+1 停牌 → T+1 開盤漲停；被剔除者不開合併窗。
    ★ T+1 開盤的可成交剔除：照登錄「同 PREREGM」字面 ＝【開盤漲停】剔除（PREREGM §三）；賣出訊號的鏡像讀法（開盤跌停剔除）另報件數與主格 X（描述）。
 V3 硬斷點、delist on、每檔每年：同 researchM_freq Q4～Q6。
 V4 主格 ＝ 甲×R5×1%（唯一判定、N_前段 ＋1）；其餘 17 格只描述（⛔ 不印判定）。⚠ 丙 不用樞紐 ⇒ R3／R5／R10 三格事件相同（照登錄 18 格全報、逐格註明）。
 V5 判語（登錄 §二）：主格 結果③（測得出（−））⇒「上升趨勢線跌破後，平均比同月其他股票差 x%」；其他 ⇒「跌破上升趨勢線，看不出之後比較會跌 ⇒ 不構成賣出理由」。
    出口照 PREREGH1 §五（n_eff ＝ min(事件數, 20 日區段數)；< 30 ①／30～99 ②／≥ 100 ③）；主 CI 月分群 CR0、非重疊 SE 第二欄。
 V6 控制組（登錄「同樣近 60 日上漲、同月、不看趨勢線」）：同一 T、gate3、近 60 日報酬 ＞ 0（還原 close_T ÷ 往前第 60 根有效 K 棒收盤 − 1）、
    該格當日無【原始】跌破、T+1 可成交（有成交、開盤非缺、非開盤漲停）、[T, T+21] 無硬斷點、非事件股 ⇒ 毛報酬等權平均；d ＝ 事件毛報酬 − 控制平均（成本相消）。
    （同一 T ⊂ 同月；⛔ 描述，不進判定）
 V7 放棄組（登錄「乙三點驗證沒過的那批」＝ researchM B14 鏡像）：主格（甲 R5 1%）保留事件依「該線確認那一根收盤時 乙（R5）的選取結果」分組；
    放棄組 ＝ 乙「第三點偏離」（三個遞升樞紐低點、第三點離 P1–P2 線 > 2%）；其餘選取結果並報。
 V8 假訊號臂（新預設，裁定 seq175／176；researchAvg A11 同）：主格；每檔抽數 ＝ 該檔主格保留真事件數；可抽日 ＝ 有效 K 棒、T ∈ [窗首, 窗尾−21]，
    排除「存在主格保留真事件 T_r ∈ [t−20, t]」的日子；不放回、⛔ 不合併；之後 硬斷點 [t, t+21] → T+1 停牌 → 開盤漲停 剔除（⛔ 不補抽）；
    種子 default_rng([20260925＋r, crc32(代號)])，r＝0…29；「不排除」版並列描述。判過 ＝ CI 不含 0（兩側，分列 ＋／−）。
    警語（鏡像 PREREGM §八）：主格為結果③ 且 假訊號（−）≥ 2／30 ⇒ 句前加「⚠ 隨機日也有 x／30 測得出（−）」。
 V9 60 日（描述）：T+61 開盤出、需 T+61 ≤ 窗尾、硬斷點範圍延伸到 T+61；60 日區段（上限 38）。
 V10 分年（T 的曆年）、上市／上櫃（快照 stocks.csv market）：主格；18 格的 X 表另列。
"""
from __future__ import annotations
import os, sys, time, json, zlib
from collections import Counter
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
import researchH2 as H2                             # ⭐ 快照、chdir ⇒ repo
D, TR, UG, R11 = H2.D, H2.TR, H2.UG, H2.R
import researchM_freq as RF                         # _g5
import researchM as TWM                             # summ、verdict、ew_open（只 import）
from backtest import trendline_ut as UT
from backtest import selftest_trendline_ut as SUT

OUT = "backtest/resultsUT"
W0, W1, WIN_DAYS, SHA = H2.W0, H2.W1, H2.WIN_DAYS, H2.SHA
COST = H2.COST_RT
H_OUT, MERGE, BLOCK, CAP = 21, 20, 20, 115
SEED, REPS = 20260925, 30
METHODS, RS, RULES = ("甲", "乙", "丙"), (3, 5, 10), ("pct1", "d3p3")
RULE_NM = {"pct1": "1%穿越", "d3p3": "3日3%"}
CELLS = [(m, R, ru) for m in METHODS for R in RS for ru in RULES]
MAIN = ("甲", 5, "pct1")


def cname(c):
    return "{}_R{}_{}".format(c[0], c[1], RULE_NM[c[2]])


def status(evs, S, w0, wE, hold=H_OUT):
    """V2：evs [(T, first, payload)] 依 T 排序 ⇒ [(T, first, payload, 狀態, f_dn)]。f_dn ＝ T+1 開盤跌停（鏡像讀法旗標）。"""
    out = []; t_keep = -10 ** 9
    for T, first, pay in evs:
        if not (w0 <= T <= wE):
            continue
        f_brk = H2.brk(S, first, T + hold)
        f_halt = (not bool(S["trd"][T + 1])) or (not np.isfinite(S["o"][T + 1]))
        f_up = bool(S["up_o"][T + 1]); f_dn = bool(S["dn_o"][T + 1])
        if t_keep < T <= t_keep + MERGE:
            st = "合併掉"
        elif f_brk:
            st = "剔除_硬斷點"
        elif f_halt:
            st = "剔除_T+1停牌"
        elif f_up:
            st = "剔除_T+1開盤漲停"
        else:
            st = "保留"; t_keep = T
        out.append((T, first, pay, st, f_dn))
    return out


def load_one(sid, market, cal, w0, w1, off):
    n = len(cal); wE = w1 - H_OUT
    st = D.load_stock(sid, market, cal)
    if st is None:
        return None
    df = st.df
    o = df["open"].to_numpy(float); h = df["high"].to_numpy(float); l = df["low"].to_numpy(float); c = df["close"].to_numpy(float)
    valid = np.isfinite(c); bars = np.flatnonzero(valid)
    if len(bars) == 0:
        return None
    pb = np.zeros(n, bool)
    for b_ in D.breakpoints(df, st.event_dates):
        if b_["rule"] in ("price", "price+gap"):
            pb[b_["pos"]] = True
    tb = TR.one(sid, cal)
    ds = TR.delist_status({sid: tb}, cal, official=off).get(sid)
    delisted = ds is not None and ds["status"].startswith("delisted")
    g5 = RF._g5(valid, upto=ds["last"]) if delisted else RF._g5(valid)
    S = {"o": o, "trd": tb["trd"], "up_o": tb["up_o"], "dn_o": tb["dn_o"], "cs_pb": np.cumsum(pb).astype(np.int32), "cs_g5": np.cumsum(g5).astype(np.int32)}
    cff = pd.Series(c).ffill().to_numpy()
    okO = valid & np.isfinite(o) & (o > 0)
    px = np.where(okO, o, cff)
    cb = c[bars]
    r60 = np.full(n, np.nan)
    if len(bars) > 60:
        r60[bars[60:]] = cb[60:] / cb[:-60] - 1.0
    cfgs, raw, why_yi = {}, {}, {}
    for m, R, ru in CELLS:
        if m == "丙" and R != 5:
            cfgs[(m, R, ru)] = cfgs.get(("丙", 5, ru))            # 丙 不用樞紐 ⇒ 同一組（V4）；R5 先算
            raw[(m, R, ru)] = raw.get(("丙", 5, ru))
            continue
        r = UT.detect_calendar(o, l, c, m, R, ru)
        evs = [(e["T"], e["first"], {"anchors": e.get("anchors"), "conf": e.get("conf"), "T_bar": e["T_bar"]}) for e in r["events"]]
        cfgs[(m, R, ru)] = status(evs, S, w0, wE)
        raw[(m, R, ru)] = np.array([e["T"] for e in r["events"]], int)
        if (m, R, ru) == ("乙", 5, "pct1"):
            why_yi = r["why_at"]
    for R in (3, 10):
        for ru in RULES:
            cfgs[("丙", R, ru)] = cfgs[("丙", 5, ru)]; raw[("丙", R, ru)] = raw[("丙", 5, ru)]
    lo_, hi_ = max(int(bars[0]), w0), min(int(bars[-1]), wE)
    return {"sid": sid, "market": market, "o": o, "c": c, "valid": valid, "bars": bars, "px": px, "okO": okO,
            "trd": tb["trd"], "up_o": tb["up_o"], "dn_o": tb["dn_o"], "cs_pb": S["cs_pb"], "cs_g5": S["cs_g5"],
            "r60": r60, "cfgs": cfgs, "raw": raw, "why_yi": why_yi, "expo": max(0, hi_ - lo_ + 1)}


def verdict_ut(s):
    ex, rs = TWM.verdict(s)
    if rs.startswith("結果③"):
        sent = "上升趨勢線跌破後，平均比同月其他股票差 {:.2f}%".format(-s["平均"] * 100)
    elif rs.startswith("結果②"):
        sent = "跌破上升趨勢線，看不出之後比較會跌（反而測得出（＋））⇒ 不構成賣出理由"
    else:
        sent = "跌破上升趨勢線，看不出之後比較會跌 ⇒ 不構成賣出理由"
    return ex, rs, sent


def main():
    t0 = time.time()
    mode = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1] in ("pre", "body") else "pre"
    lim = int(sys.argv[sys.argv.index("--limit") + 1]) if "--limit" in sys.argv else None
    fx = SUT.run_all()
    fxm = TWM.selftest()
    cal = D.load_calendar(); n = len(cal)
    w0 = int(cal.searchsorted(pd.Timestamp(W0))); w1 = int(cal.searchsorted(pd.Timestamp(W1)))
    assert str(cal[w0].date()) == W0 and str(cal[w1].date()) == W1 and w1 - w0 + 1 == WIN_DAYS
    wE = w1 - H_OUT
    stocks = pd.read_csv(os.path.join(H2.H2D, "meta", "stocks.csv"), dtype=str)
    U = UG.gate3(stocks)
    if lim:
        U = U.head(lim)
    off = TR.load_official()
    print("[資料] 快照 {}｜判定窗 [{}, {}]｜T 可落 [{}, {}]｜gate3 {:,} 檔｜{}".format(SHA[:10], W0, W1, cal[w0].date(), cal[wE].date(), len(U), mode), flush=True)
    ST = {}
    for sid, mk in zip(U["stock_id"], U["market"]):
        r = load_one(sid, mk, cal, w0, w1, off)
        if r is not None:
            ST[sid] = r
    sids = sorted(ST)
    print("[讀檔＋偵測] 可用 {:,} 檔｜{:.0f}s".format(len(ST), time.time() - t0), flush=True)
    os.makedirs(OUT, exist_ok=True)
    DPY = (wE - w0 + 1) / ((cal[wE] - cal[w0]).days / 365.25)

    def acct(key):
        a = Counter(x[3] for s in sids for x in ST[s]["cfgs"][key])
        kept_dn = sum(1 for s in sids for x in ST[s]["cfgs"][key] if x[3] == "保留" and x[4])
        return {"原始_窗內": int(sum(a.values())), "合併掉": a["合併掉"], "剔除_硬斷點": a["剔除_硬斷點"], "剔除_T+1停牌": a["剔除_T+1停牌"],
                "剔除_T+1開盤漲停": a["剔除_T+1開盤漲停"], "保留": a["保留"], "保留中_T+1開盤跌停（鏡像讀法會再剔除）": kept_dn}

    # ── pre：頻率與可判定性（⛔ 只數日期）
    FREQ = {}
    for cell in CELLS:
        a = acct(cell)
        kT = [(s, x[0]) for s in sids for x in ST[s]["cfgs"][cell] if x[3] == "保留"]
        blk = len({min((T - w0) // BLOCK, CAP - 1) for _, T in kT})
        per = pd.DataFrame([(ST[s]["expo"] / DPY, sum(1 for x in ST[s]["cfgs"][cell] if x[3] == "保留")) for s in sids if ST[s]["expo"] > 0], columns=["yrs", "n"])
        one = per[per["yrs"] >= 1]
        ne = min(len(kT), blk)
        FREQ[cname(cell)] = {"事件帳": a, "有事件的20日區段": blk, "n_eff": ne, "出口上限": "出口③" if ne >= 100 else ("出口②" if ne >= 30 else "出口①"),
                             "每檔每年": {"合併比率": round(float(per["n"].sum() / per["yrs"].sum()), 4), "平均": round(float((one["n"] / one["yrs"]).mean()), 4),
                                       "中位": round(float((one["n"] / one["yrs"]).median()), 4)}}
        print("[頻率] {:16s} 原始 {:>6,}｜合併 {:>6,}｜剔除 斷點 {}／停牌 {}／漲停 {}｜保留 {:>6,}｜(跌停 {})｜區段 {}｜n_eff {}｜每檔每年 {}".format(
            cname(cell), a["原始_窗內"], a["合併掉"], a["剔除_硬斷點"], a["剔除_T+1停牌"], a["剔除_T+1開盤漲停"], a["保留"],
            a["保留中_T+1開盤跌停（鏡像讀法會再剔除）"], blk, ne, FREQ[cname(cell)]["每檔每年"]["合併比率"]), flush=True)
    PRE = {"性質": "PREREG上升趨勢線 pre（⛔ 未讀 T+1 以後任何價格）", "快照": SHA, "判定窗": [W0, W1], "gate3母體": int(len(U)), "可用檔數": len(ST),
           "fixture_trendline_ut": fx, "fixture_researchM自測": fxm, "每年交易日": DPY, "區段上限": CAP, "格": FREQ,
           "V4_丙三個R相同": True, "主格": cname(MAIN)}
    json.dump(PRE, open(os.path.join(OUT, "pre_freq.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    rows = []
    for cell in CELLS:
        if cell[0] == "丙" and cell[1] != 5:
            continue
        for s in sids:
            for T, first, pay, stt, fdn in ST[s]["cfgs"][cell]:
                rows.append({"格": cname(cell), "sid": s, "market": ST[s]["market"], "T": str(cal[T].date()), "first": str(cal[first].date()),
                             "anchors": "|".join(str(cal[a_].date()) for a_ in pay["anchors"]) if pay.get("anchors") else "",
                             "conf": str(cal[pay["conf"]].date()) if pay.get("conf") is not None else "", "狀態": stt, "T+1開盤跌停": int(fdn)})
    pd.DataFrame(rows).to_csv(os.path.join(OUT, "pre_events.csv.gz"), index=False)
    if mode == "pre":
        print("pre 完成 {:.0f}s".format(time.time() - t0)); return

    # ═════════════ 本體 ═════════════
    O = np.column_stack([ST[s]["o"] for s in sids]); okO = np.column_stack([ST[s]["okO"] for s in sids])
    PX = np.column_stack([ST[s]["px"] for s in sids])
    EW = {H: TWM.ew_open(O, okO, PX, H) for H in (20, 60)}
    sidx = {s: i for i, s in enumerate(sids)}

    def kept_df(cell, dn_too=False):
        rr = []
        for s in sids:
            S = ST[s]
            for T, first, pay, stt, fdn in S["cfgs"][cell]:
                if stt != "保留" or (dn_too and fdn):
                    continue
                g = S["px"][T + H_OUT] / S["o"][T + 1] - 1.0
                rr.append({"sid": s, "market": S["market"], "T": T, "first": first, "g": g, "R": g - COST, "EW": EW[20][T + 1],
                           "X": g - EW[20][T + 1], "conf": pay.get("conf"), "anchors": pay.get("anchors")})
        return pd.DataFrame(rr)

    RES = {"性質": "PREREG上升趨勢線 本體（主格判定一格，N_前段 ＋1）", "快照": SHA, "判定窗": [W0, W1], "可用檔數": len(ST), "成本": COST, "格": {}}
    E = {}
    for cell in CELLS:
        e = kept_df(cell); E[cell] = e
        s_ = TWM.summ(e["X"], e["T"], cal, w0)
        sR = TWM.summ(e["R"], e["T"], cal, w0)
        d = {**s_, "事件帳": FREQ[cname(cell)]["事件帳"], "R_e平均": sR["平均"], "R_e中位": sR["中位"], "丙三個R相同": cell[0] == "丙"}
        if cell == MAIN:
            ex, rs, sent = verdict_ut(s_)
            d.update({"出口": ex, "結果": rs, "判語": sent})
        RES["格"][cname(cell)] = d
        print("[{:16s}] n {:>6,}｜X {:+.3%}（{:+.3%} ～ {:+.3%}）｜n_eff {}{}".format(cname(cell), s_["n"], s_["平均"], s_["lo"], s_["hi"], s_["n_eff"],
              "｜⭐ " + d["出口"] + " " + d["結果"] if cell == MAIN else ""), flush=True)
    em = E[MAIN]
    # V2 鏡像讀法：再剔除 T+1 開盤跌停（描述）
    e2 = kept_df(MAIN, dn_too=True); s2 = TWM.summ(e2["X"], e2["T"], cal, w0)
    RES["V2_鏡像讀法_再剔除T+1開盤跌停（主格，描述）"] = {"n": s2["n"], "平均": s2["平均"], "lo": s2["lo"], "hi": s2["hi"], "n_eff": s2["n_eff"],
                                                 "結果（照同一判法，只描述）": TWM.verdict(s2)[1]}
    # V10 分年、上市／上櫃
    yr = np.array([cal[t].year for t in em["T"]])
    RES["主格_逐年"] = {str(y): {k: TWM.summ(em["X"][yr == y], em["T"][yr == y], cal, w0)[k] for k in ("n", "平均", "lo", "hi")} for y in sorted(set(yr))}
    RES["主格_上市上櫃"] = {nm: {k: TWM.summ(em.loc[em["market"] == mk, "X"], em.loc[em["market"] == mk, "T"], cal, w0)[k] for k in ("n", "平均", "lo", "hi")}
                          for mk, nm in (("twse", "上市"), ("tpex", "上櫃"))}
    # V9 60 日
    c60 = {}
    for cell in CELLS:
        if cell[0] == "丙" and cell[1] != 5:
            continue
        xs, Ts, sw, sb = [], [], 0, 0
        for ev in E[cell].itertuples():
            S = ST[ev.sid]; T = int(ev.T)
            if T + 61 > w1:
                sw += 1; continue
            if H2.brk({"cs_pb": S["cs_pb"], "cs_g5": S["cs_g5"]}, int(ev.first), T + 61):
                sb += 1; continue
            g = S["px"][T + 61] / S["o"][T + 1] - 1.0
            xs.append(g - EW[60][T + 1]); Ts.append(T)
        s6 = TWM.summ(xs, Ts, cal, w0, blk=60, cap=WIN_DAYS // 60)
        c60[cname(cell)] = {k: s6.get(k) for k in ("n", "平均", "lo", "hi", "n_eff")} | {"排除_超窗尾": sw, "排除_延伸段斷點": sb}
    RES["60日（描述）"] = c60
    # V6 控制組
    VAL = np.column_stack([ST[s]["valid"] for s in sids]); R60 = np.column_stack([ST[s]["r60"] for s in sids])
    TRD1 = np.column_stack([ST[s]["trd"] & np.isfinite(ST[s]["o"]) & ~ST[s]["up_o"] for s in sids])
    HB = np.zeros((n, len(sids)), bool); Tr = np.arange(1, n - H_OUT)
    for i, s in enumerate(sids):
        S = ST[s]
        HB[Tr, i] = ((S["cs_pb"][Tr + H_OUT] - S["cs_pb"][Tr - 1]) > 0) | ((S["cs_g5"][Tr + H_OUT] - S["cs_g5"][Tr + 3]) > 0)
    G20 = np.full((n, len(sids)), np.nan); Od = np.where(okO, O, np.nan)
    with np.errstate(invalid="ignore", divide="ignore"):
        G20[:n - H_OUT] = PX[H_OUT:] / Od[1:n - H_OUT + 1] - 1.0
    ctl = {}
    for cell in [c_ for c_ in CELLS if not (c_[0] == "丙" and c_[1] != 5)]:
        RAW = np.zeros((n, len(sids)), bool)
        for s in sids:
            RAW[ST[s]["raw"][cell], sidx[s]] = True
        rows = []; nov = 0; nc = []
        for T, grp in E[cell].groupby("T"):
            el = VAL[T] & (R60[T] > 0) & TRD1[T + 1] & ~HB[T] & ~RAW[T] & np.isfinite(G20[T])
            for ev in grp.itertuples():
                cm = el.copy(); cm[sidx[ev.sid]] = False
                if not cm.any():
                    nov += 1; continue
                mu = float(G20[T, cm].mean())
                rows.append({"T": T, "d": ev.g - mu, "ev_up": bool(R60[T, sidx[ev.sid]] > 0)}); nc.append(int(cm.sum()))
        Dd = pd.DataFrame(rows)
        s_ = TWM.summ(Dd["d"], Dd["T"], cal, w0)
        ctl[cname(cell)] = {k: s_.get(k) for k in ("n", "平均", "lo", "hi")} | {"無控制而略過": nov, "每事件控制數中位": float(np.median(nc)) if nc else None,
                                                                       "事件股本身近60日上漲的比例": float(Dd["ev_up"].mean()) if len(Dd) else None}
    RES["控制組_同T近60日上漲不看趨勢線（描述）"] = ctl
    # V7 放棄組
    ea = em.copy()
    ea["乙選取"] = [ST[s]["why_yi"].get(int(cf), "（該根無乙選取）") for s, cf in zip(ea["sid"], ea["conf"])]
    RES["放棄組_乙三點驗證沒過（主格事件依乙選取分組，描述）"] = {w: {k: TWM.summ(g["X"], g["T"], cal, w0)[k] for k in ("n", "平均", "lo", "hi")}
                                                    for w, g in ea.groupby("乙選取")}
    # V8 假訊號臂
    fk = []
    realT = {s: np.sort(g["T"].to_numpy()) for s, g in em.groupby("sid")}
    for vi, vn in enumerate(("新預設_只排除過去20日", "不排除（描述）")):
        cand = {}
        for s in realT:
            S = ST[s]; b = S["bars"]; b = b[(b >= w0) & (b <= wE)]
            if vi == 0:
                rt = realT[s]; k_ = np.searchsorted(rt, b, side="right")
                prev = np.where(k_ > 0, rt[np.maximum(k_ - 1, 0)], -10 ** 9)
                b = b[~((k_ > 0) & (b - prev <= 20))]
            cand[s] = b
        for r in range(REPS):
            xs, Ts = [], []; acc = Counter()
            for s in sorted(realT):
                S = ST[s]; SS = {"cs_pb": S["cs_pb"], "cs_g5": S["cs_g5"]}
                rng = np.random.default_rng([SEED + r, zlib.crc32(s.encode()), vi])
                k = min(len(realT[s]), len(cand[s]))
                for T in np.sort(rng.choice(cand[s], size=k, replace=False)) if k else []:
                    T = int(T)
                    if H2.brk(SS, T, T + H_OUT):
                        acc["斷點"] += 1; continue
                    if (not S["trd"][T + 1]) or not np.isfinite(S["o"][T + 1]):
                        acc["停牌"] += 1; continue
                    if S["up_o"][T + 1]:
                        acc["漲停"] += 1; continue
                    acc["保留"] += 1
                    xs.append(S["px"][T + H_OUT] / S["o"][T + 1] - 1.0 - EW[20][T + 1]); Ts.append(T)
            sf = TWM.summ(xs, Ts, cal, w0)
            pas = not (sf["lo"] <= 0 <= sf["hi"])
            fk.append({"版本": vn, "r": r, "保留": sf["n"], "平均X": sf["平均"], "lo": sf["lo"], "hi": sf["hi"], "n_eff": sf["n_eff"],
                       "判過": pas, "判過_正": bool(pas and sf["平均"] > 0), "判過_負": bool(pas and sf["平均"] < 0), **{"剔除_" + k_: v_ for k_, v_ in acc.items() if k_ != "保留"}})
        print("[假訊號臂] {} 完成｜{:.0f}s".format(vn, time.time() - t0), flush=True)
    FK = pd.DataFrame(fk); FK.to_csv(os.path.join(OUT, "fake_arm.csv"), index=False)
    fake = {vn: {"x／30": int(g["判過"].sum()), "其中(+)": int(g["判過_正"].sum()), "其中(−)": int(g["判過_負"].sum()),
                 "30次平均X的平均": float(g["平均X"].mean()), "範圍": [float(g["平均X"].min()), float(g["平均X"].max())], "平均保留數": float(g["保留"].mean())}
            for vn, g in FK.groupby("版本")}
    RES["假訊號臂（主格）"] = fake
    J = RES["格"][cname(MAIN)]
    J["警語"] = ("⚠ 隨機日也有 {}／30 測得出（−）".format(fake["新預設_只排除過去20日"]["其中(−)"])
                 if (J["結果"].startswith("結果③") and fake["新預設_只排除過去20日"]["其中(−)"] >= 2) else "無")
    # 先驗（登錄 §五）
    RES["先驗_主格分不出或負但與同月弱勢分不開（押約七成）"] = {"主格結果": J["結果"], "控制組差": ctl[cname(MAIN)], "假訊號新預設": fake["新預設_只排除過去20日"]}
    # 逐筆（台股，可入庫）
    out = []
    for cell in CELLS:
        if cell[0] == "丙" and cell[1] != 5:
            continue
        e = E[cell].drop(columns=["anchors"]).copy(); e.insert(0, "格", cname(cell))
        e["T_date"] = [str(cal[t].date()) for t in e["T"]]
        out.append(e)
    pd.concat(out, ignore_index=True).to_csv(os.path.join(OUT, "events_X.csv.gz"), index=False)
    RES["fixture"] = {"trendline_ut": fx, "researchM自測": fxm}
    RES["耗時s"] = round(time.time() - t0)
    json.dump(RES, open(os.path.join(OUT, "summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    print("主格：{} {}｜{}｜{}".format(J["出口"], J["結果"], J["判語"], J["警語"]))
    print("完成 {:.0f}s".format(time.time() - t0))


if __name__ == "__main__":
    main()

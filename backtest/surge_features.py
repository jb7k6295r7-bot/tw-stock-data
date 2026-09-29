# -*- coding: utf-8 -*-
"""飆股回推（PREREG飆股回推 seq4，sha abe83459d08eca7a）的特徵庫：可 import 的模組（§九 另一子代理沿用）。回測線，2026-09-29。

用法（另一支程式）：
    from backtest import surge_features as SF
    W = SF.world("主")            # 或 "早年"
    T = SF.table(W, procs=2)      # 母體股-日 × 特徵原值＋標籤＋後續報酬（一列 ＝ 觀察日 d 的一檔）
    T = SF.cross(T, W)            # 橫斷面：五等分、產業排名、基準② X
    SF.FEATS                      # 特徵清單：(名稱, 類別, 型態, 原值欄, 資料起, 舊結論)

═══ 口徑（⭐ 看任何本件數字前寫死）═══
 列 ＝ 觀察日 d（有效 K 棒）× 股票；「起漲日」t ＝ d＋1（t 當日 W1 eligible、t 有有效 K 棒）；特徵只用 d 收盤以前（＝ t−1 以前）可得資料
 標籤 F1／F2／F3：(t, t＋H] 內 c_ff 最高 ≥ c[t] × (1＋g)（H 60／20／120、g 100%／50%／200%；交易日曆；c_ff ＝ 收盤 ffill）；
   (t, t＋H] 跨資料尾或含壞根（research11.load_bars：相位事件、斷點、≥5 日缺口）⇒ 該 F 的標籤 NaN（不進分母，計數必報）；
   同一檔：成立的 t 之後 H 日內再成立的日子不算新事件（取第一天）——⚠ 那些日子仍留在母體、標籤 0（登錄「對照母體 ＝ 全體股-日」逐字）
 妖股（F1 事件內）：高點 ＝ (t, t＋60] 內最高 c_ff 那天 p；(p, p＋60] 最低 c_ff ≤ 高點 × 0.5；p＋60 跨資料尾或含壞根 ⇒ NaN
 後續報酬（③）：R_h ＝ c_ff[d＋h] ÷ 開[d＋1] − 1（＝ t 開盤買、持有 h；PREREG事件 E4 同式）；d＋1 不可買（無成交、開盤無效、開盤漲停）⇒ NaN；
   d＋h 跨資料尾 ⇒ NaN；有效 K 棒 [k_d−19, k_x] 內有壞根 ⇒ NaN；基準② ＝ 同 d、母體中 R_h 有限者依前 20 日報酬（avgdown.r20_cal）十分位、同十分位其他股平均
 母體 ＝ W1 eligible（量測日面板、到下一個量測日前有效；主 panel_ext 舊快取；早年 sig_main/panel：2012-06 起 W1、之前 liq∧bars）∩ gate3（innov_ky 開）
 資料（主）：tw-stock-data main b53f5540a8（git archive 唯讀 ~/h2data/surge_b53f5540a8ad）；早年 ＝ 早年版面 ~/earlydata/3edc0e2206/main（只上市）
 特徵（登錄 §二、§七、§八；§九 另件）見 FEATS；連續型 ＝ 當日母體內五等分（1 低～5 高；avgdown 同式 rank×5//n、同值依代號），另存原值
 ⛔ 做不到、照實剔除：分點主力（官方無歷史）；集保（tdcc_hist 是 parquet、本機無讀取套件 ⇒ 待協調者裁示，暫缺）
 早年無資料：財報（fin_hist 2013 起）、法人、融資、借券、集保、注意／處置（2010-12／2011 起、只涵蓋一部分 ⇒ 不驗）
"""
from __future__ import annotations

import glob
import os
import sys
from multiprocessing import Pool

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
from backtest import data as D
from backtest import tradability as TR
from backtest import universe_gate as UG
from backtest import research11 as R11
from backtest import research34 as R34
from backtest import p4_features as P4F
from backtest import avgdown as AV

UG.set_innov_ky(True)
MAIN_SHA = "b53f5540a8add6927d72d57d010466631d4bfb08"
MAIN_DATA = os.path.expanduser(f"~/h2data/surge_{MAIN_SHA[:12]}/data")
EARLY_DATA = os.path.expanduser("~/earlydata/3edc0e2206/main/data")
MPANEL = os.path.expanduser("~/tw-p17/backtest/resultsp9_engine/panel_ext.csv.gz")
EPANEL = os.path.expanduser("~/earlydata/3edc0e2206/sig_main/panel.csv.gz")
EARLY_REV = os.path.join(EARLY_DATA, "mops", "revenue_hist")
FDEF = {"F1": (60, 1.0), "F2": (20, 0.5), "F3": (120, 2.0)}
HS = (20, 60, 120)
SPAN = {"主": ("2017-03-01", "2026-08-31"), "早年": ("2005-01-01", "2014-12-31")}

# (名稱, 類別, 型態, 原值欄, 主窗資料起, 早年可用, 舊結論)
#   型態：bin（1＝有）｜q5（五等分 1～5）｜lvl（事先寫死的級距，值 ＝ 級距碼）
OLD = {"創新高": "舊結論：股價創新高 單測測不出（本專案單測）",
       "多頭": "舊結論：營量趨勢（PREREG營量趨勢）趨勢過濾 確認段好、早年差；多頭排列加在營量上不穩",
       "量縮": "舊結論：K線 研究十二「事前量縮」20／60 天偏弱（9/28 還原價重跑、正式）",
       "橫盤": "舊結論：K線 研究十二 橫盤／波動收縮類偏弱；不追高、等早鳥沒有一格贏追高",
       "股性": "舊結論：營量 v1 5 取 3 的「20 日漲停 ≥ 3 次」是條件之一（強勢 5 取 3 單獨不等於飆股）",
       "營收": "舊結論：營收創 24 月新高 單測有效（營量 v1／營飆 v1 的核心條件）",
       "價量": "舊結論：價量齊揚 單測測不出"}
FEATS = [
    ("營收創24月新高", "營收", "bin", "f_revhi", "2017", True, OLD["營收"]),
    ("營收年增率", "營收", "q5", "v_yoy", "2017", True, ""),
    ("營收月增率", "營收", "q5", "v_mom", "2017", True, ""),
    ("連續年增月數", "營收", "q5", "v_streak", "2017", True, ""),
    ("距24月最高營收", "營收", "q5", "v_d24", "2017", True, ""),
    ("R1營收轉折", "營收", "bin", "f_R1", "2017", True, ""),
    ("R2營收年增≥50%", "營收", "bin", "f_R2a", "2017", True, ""),
    ("R2營收年增≥100%", "營收", "bin", "f_R2b", "2017", True, ""),
    ("EPS轉正", "財報A2", "bin", "f_eps", "2017", False, ""),
    ("毛利率比上季升", "財報A2", "bin", "f_gm", "2017", False, ""),
    ("營益率比去年同季升", "財報A2", "bin", "f_opm", "2017", False, ""),
    ("ROE", "財報A2", "q5", "v_roe", "2017", False, ""),
    ("外資5日淨買÷股本", "法人", "q5", "v_f5", "2017", False, ""),
    ("外資20日淨買÷股本", "法人", "q5", "v_f20", "2017", False, ""),
    ("投信5日淨買÷股本", "法人", "q5", "v_t5", "2017", False, ""),
    ("投信20日淨買÷股本", "法人", "q5", "v_t20", "2017", False, ""),
    ("投信連買天數", "法人", "lvl", "l_tstreak", "2017", False, ""),
    ("融資20日變化÷股本", "融資", "q5", "v_m20", "2017", False, ""),
    ("融資使用率", "融資", "q5", "v_mu", "2017", False, ""),
    ("停止融資", "融資", "bin", "f_mstop", "2017", False, ""),
    ("借券賣出餘額20日變化÷股本", "借券", "q5", "v_sbl20", "2017", False, ""),
    ("5日報酬", "價", "q5", "v_r5", "2017", True, ""),
    ("20日報酬", "價", "q5", "v_r20", "2017", True, OLD["價量"]),
    ("60日報酬", "價", "q5", "v_r60", "2017", True, ""),
    ("120日報酬", "價", "q5", "v_r120", "2017", True, ""),
    ("距250日高", "價", "q5", "v_dhi", "2017", True, OLD["創新高"]),
    ("距250日低", "價", "q5", "v_dlo", "2017", True, ""),
    ("均線多頭排列5>20>60>100", "價", "bin", "f_bull", "2017", True, OLD["多頭"]),
    ("收盤站上MA100", "價", "bin", "f_ma100", "2017", True, ""),
    ("20日漲停天數", "價", "lvl", "l_lu20", "2017", True, OLD["股性"]),
    ("布林帶寬250日分位", "價", "q5", "v_bbw", "2017", True, OLD["橫盤"]),
    ("當日額÷前20日均額", "量", "q5", "v_ar", "2017", True, OLD["價量"]),
    ("20日均額÷前120日均額", "量", "q5", "v_a20120", "2017", True, OLD["量縮"]),
    ("周轉率", "量", "q5", "v_turn", "2017", True, ""),
    ("市值", "規模", "q5", "v_mcap", "2017", True, ""),
    ("股本", "規模", "q5", "v_shares", "2017", True, ""),
    ("股價級距", "規模", "lvl", "l_px", "2017", True, ""),
    ("產業20日報酬排名", "產業", "q5", "v_indrk", "2017", True, ""),
    ("0050在200日線上", "大盤", "bin", "f_mkt", "2017", True, ""),
    ("注意股60日次數", "注意處置", "lvl", "l_att", "2017", False, ""),
    ("60日內曾處置", "注意處置", "bin", "f_disp", "2017", False, ""),
    ("K1 KD高檔鈍化(K>80連3日)", "K", "bin", "f_K1", "2017", True, ""),
    ("K1 K>80連續天數", "K", "lvl", "l_K1", "2017", True, ""),
    ("K2 布林上軌帶量突破", "K", "bin", "f_K2", "2017", True, ""),
    ("K3 RSI14>50", "K", "bin", "f_K3a", "2017", True, ""),
    ("K3 RSI6上穿RSI12", "K", "bin", "f_K3b", "2017", True, ""),
    ("K4 均線糾結後發動", "K", "bin", "f_K4", "2017", True, OLD["橫盤"]),
    ("K5 周轉率≥10%", "K", "bin", "f_K5a", "2017", True, ""),
    ("K5 周轉率≥20%", "K", "bin", "f_K5b", "2017", True, ""),
    ("V1 量縮盤整後帶量突破", "V", "bin", "f_V1", "2017", True, OLD["量縮"]),
    ("V2 EMA20>SMA20連續天數", "V", "lvl", "l_V2", "2017", True, ""),
    ("V3 修正箱突破", "V", "bin", "f_V3", "2017", True, ""),
]
LVL = {"l_tstreak": {0: "0 天", 1: "1～2 天", 2: "3～5 天", 3: "≥6 天"}, "l_lu20": {0: "0 次", 1: "1 次", 2: "2 次", 3: "≥3 次"},
       "l_px": {0: "＜20 元", 1: "20～50 元", 2: "50～100 元", 3: "≥100 元"}, "l_att": {0: "0 次", 1: "1～2 次", 2: "≥3 次"},
       "l_K1": {0: "0 天", 1: "1～2 天", 2: "3～5 天", 3: "≥6 天"}, "l_V2": {0: "0 天", 1: "1～4 天", 2: "5～9 天", 3: "≥10 天"}}
_G: dict = {}


# ═════════════ 世界 ═════════════
def world(tag):
    main = tag == "主"
    data = MAIN_DATA if main else EARLY_DATA
    D.DATA = data
    cal = D.load_calendar(); n = len(cal)
    stocks = pd.read_csv(os.path.join(data, "meta", "stocks.csv"), dtype=str)
    uni = D.load_universe().merge(UG.gate3(stocks)[["stock_id"]], on="stock_id")
    W = {"tag": tag, "data": data, "cal": cal, "sids": list(zip(uni["stock_id"], uni["market"])), "main": main}
    # 母體
    pan = pd.read_csv(MPANEL if main else EPANEL, dtype={"stock_id": str}, parse_dates=["measure_date"])
    tf = lambda s: s.astype(str).isin(["True", "1", "1.0"])
    mds = sorted(pan["measure_date"].unique()); EL = {}
    for i, md in enumerate(mds):
        g = pan[pan["measure_date"] == md]
        el = tf(g["eligible"]) if (main or md >= pd.Timestamp("2012-06-01")) else (tf(g["liq_ok"]) & tf(g["bars_ok"]))
        a = int(cal.searchsorted(md)); b = int(cal.searchsorted(mds[i + 1])) if i + 1 < len(mds) else n
        for s in g.loc[el.to_numpy(), "stock_id"]:
            EL.setdefault(s, np.zeros(n, bool))[a:b] = True
    W["EL"] = EL
    # 月營收（早年版面 2003～2014 ＋ 主快照；researchMLlite 同一份接法）
    fs = sorted(glob.glob(os.path.join(EARLY_REV, "*.csv"))) + (sorted(glob.glob(os.path.join(data, "mops", "revenue_hist", "*.csv"))) if main else [])
    df = pd.concat([pd.read_csv(f, dtype=str, usecols=["stock_id", "period", "當月營收"]) for f in fs])
    df["rev"] = pd.to_numeric(df["當月營收"], errors="coerce"); df = df.drop_duplicates(["stock_id", "period"], keep="last")
    rev = df.pivot(index="period", columns="stock_id", values="rev").sort_index()
    W["REV"] = rev; W["REVFLAG"] = P4F.rev_hi24_flags(rev, cal)
    rd = R34.rebalance_dates(list(rev.index), cal, 10)
    W["REV_EFF"] = np.array([rd[p][1] if p in rd else (n + 10 if pd.Period(p) > pd.Period(str(cal[-1])[:7]) else -1) for p in rev.index])
    # 0050
    b = pd.Series(D.load_stock("0050", "twse", cal).df["close"].to_numpy(float)).ffill().to_numpy()
    W["MKT"] = (b > pd.Series(b).rolling(200).mean().to_numpy()).astype(float)
    W["MKT"][:199] = np.nan
    ind = pd.read_csv(os.path.join(MAIN_DATA, "meta", "industry.csv"), dtype=str)
    W["IND"] = dict(zip(ind["stock_id"], ind["industry_code"]))
    if main:
        W.update(fin_table(data, cal)); W["SBL"] = sbl_series(data, cal); W["ATT"], W["DISP"] = att_disp(data, cal)
    return W


def fin_table(data, cal):
    """財報 A2（researchQual B2 同式：有 t57sb01 時戳用時戳次一交易日；其餘法定期限次一交易日再 ＋5）。回 {sid: (可用位置, eps, gm, opm, roe)}（依季排序）。"""
    fs = sorted(glob.glob(os.path.join(data, "mops", "fin_hist", "*.csv")))
    cols = ["stock_id", "period", "rev_q", "opi_q", "gp_q", "eps_q", "ni_ytd", "nip_ytd", "equity_parent", "equity_total"]
    F = pd.concat([pd.read_csv(f, dtype={"stock_id": str, "period": str}, usecols=cols) for f in fs], ignore_index=True).drop_duplicates(["stock_id", "period"], keep="last")
    F["y"] = F["period"].str[:4].astype(int); F["q"] = F["period"].str[-1].astype(int)
    fd = pd.read_csv(os.path.join(data, "meta", "filing_dates.csv"), dtype={"stock_id": str})
    fd["d"] = pd.to_datetime(fd["uploaded_at"].astype(str).str[:10], errors="coerce")
    fdm = fd.dropna(subset=["d"]).groupby(["stock_id", "year", "season"])["d"].min().to_dict()
    dl = {1: (5, 15), 2: (8, 14), 3: (11, 14)}
    K = {(s, y, q): r for s, y, q, r in zip(F["stock_id"], F["y"], F["q"], F.to_dict("records"))}
    out = {}
    for s, g in F.sort_values(["stock_id", "y", "q"]).groupby("stock_id"):
        rows = []
        for r in g.to_dict("records"):
            y, q = r["y"], r["q"]
            ts = fdm.get((s, y, q))
            if ts is not None:
                pos = int(cal.searchsorted(ts, side="right"))
            else:
                d0 = pd.Timestamp(y + 1, 3, 31) if q == 4 else pd.Timestamp(y, *dl[q])
                pos = int(cal.searchsorted(d0, side="right")) + 5
            rq = r["rev_q"]
            gm = r["gp_q"] / rq if (np.isfinite(r["gp_q"]) and np.isfinite(rq) and rq > 0) else np.nan
            opm = r["opi_q"] / rq if (np.isfinite(r["opi_q"]) and np.isfinite(rq) and rq > 0) else np.nan
            # ROE（researchQual Q1 同式）
            def ttm(col):
                cur = K.get((s, y, q), {}).get(col, np.nan)
                if q == 4:
                    return float(cur)
                fy = K.get((s, y - 1, 4), {}).get(col, np.nan); ly = K.get((s, y - 1, q), {}).get(col, np.nan)
                return float(fy + cur - ly) if np.isfinite(fy) and np.isfinite(cur) and np.isfinite(ly) else np.nan
            py, pq = (y, q - 1) if q > 1 else (y - 1, 4); prv = K.get((s, py, pq), {})
            avg2 = lambda a_, b_: (a_ + b_) / 2 if np.isfinite(a_) and np.isfinite(b_) else np.nan
            nip, ni = ttm("nip_ytd"), ttm("ni_ytd")
            ep = avg2(r["equity_parent"], prv.get("equity_parent", np.nan)); et = avg2(r["equity_total"], prv.get("equity_total", np.nan))
            if np.isfinite(nip) and np.isfinite(ep):
                roe = nip / ep if ep > 0 else np.nan
            else:
                roe = ni / et if np.isfinite(ni) and np.isfinite(et) and et > 0 else np.nan
            rows.append((pos, y, q, float(r["eps_q"]), gm, opm, roe))
        out[s] = rows
    return {"FIN": out}


def sbl_series(data, cal):
    n = len(cal); out = {}
    for sub in ("sbl", "otcsbl"):
        for f in sorted(glob.glob(os.path.join(data, "universe", sub, "*.csv"))):
            x = pd.read_csv(f, dtype={"stock_id": str, "date": str}, usecols=["date", "stock_id", "sbl_balance"])
            if not len(x):
                continue
            p = int(cal.searchsorted(pd.Timestamp(x["date"].iloc[0])))
            if p >= n or cal[p] != pd.Timestamp(x["date"].iloc[0]):
                continue
            for s, v in zip(x["stock_id"], pd.to_numeric(x["sbl_balance"], errors="coerce")):
                out.setdefault(s, {})[p] = v
    first = min((min(v) for v in out.values()), default=0)
    return {"first": first, "S": out}


def att_disp(data, cal):
    a = pd.read_csv(os.path.join(data, "meta", "attention.csv"), dtype={"stock_id": str, "date": str}, usecols=["stock_id", "date"])
    A = {}
    for s, g in a.groupby("stock_id"):
        A[s] = np.unique(cal.searchsorted(pd.to_datetime(g["date"])))
    d = pd.read_csv(os.path.join(data, "meta", "disposal.csv"), dtype={"stock_id": str}, usecols=["stock_id", "start_date", "end_date"])
    Dp = {}
    for s, g in d.groupby("stock_id"):
        Dp[s] = [(int(cal.searchsorted(pd.Timestamp(x))), int(cal.searchsorted(pd.Timestamp(y), side="right")) - 1) for x, y in zip(g["start_date"], g["end_date"])]
    return A, Dp


# ═════════════ 每檔 ═════════════
def _roll(x, w, fn):
    return getattr(pd.Series(x).rolling(w, min_periods=w), fn)().to_numpy()


def kd(C, H, L):
    n = len(C); K = np.full(n, np.nan); k0 = d0 = 50.0
    for t in range(8, n):
        lo, hi = L[t - 8:t + 1].min(), H[t - 8:t + 1].max()
        rsv = 50.0 if hi - lo <= 0 else (C[t] - lo) / (hi - lo) * 100
        k0 = k0 * 2 / 3 + rsv / 3; d0 = d0 * 2 / 3 + k0 / 3; K[t] = k0
    return K


def rsi(C, n_):
    out = np.full(len(C), np.nan)
    if len(C) <= n_:
        return out
    d = np.diff(C); g = np.maximum(d, 0); l_ = np.maximum(-d, 0)
    ag, al = g[:n_].mean(), l_[:n_].mean()
    for t in range(n_, len(C)):
        if t > n_:
            ag = (ag * (n_ - 1) + g[t - 1]) / n_; al = (al * (n_ - 1) + l_[t - 1]) / n_
        out[t] = 100.0 if al == 0 else 100 - 100 / (1 + ag / al)
    return out


def ema(x, n_):
    a = 2.0 / (n_ + 1); out = np.empty(len(x)); out[0] = x[0]
    for t in range(1, len(x)):
        out[t] = a * x[t] + (1 - a) * out[t - 1]
    return out


def run_len(flag):
    out = np.zeros(len(flag), int); r = 0
    for i, f in enumerate(flag):
        r = r + 1 if f else 0; out[i] = r
    return out


def _init(W):
    D.DATA = W["data"]; _G.clear(); _G.update(W)


def stock(args):
    sid, mk = args
    W = _G; cal = W["cal"]; n = len(cal); main = W["main"]
    el = W["EL"].get(sid)
    if el is None:
        return None
    B = R11.load_bars(sid, mk, cal)
    if B is None:
        return None
    st = D.load_stock(sid, mk, cal); df = st.df
    idx, o, c, h, l, amt, up, nb = (B[k] for k in ("idx", "o", "c", "h", "l", "amt", "up", "next_bad"))
    m = len(idx)
    cfull = df["close"].to_numpy(float); cff = pd.Series(cfull).ffill().to_numpy(); ofull = df["open"].to_numpy(float)
    vol = pd.to_numeric(df["volume"], errors="coerce").to_numpy(float)[idx]
    raw = pd.read_csv(os.path.join(W["data"], "stocks", sid + ".csv"), dtype={"date": str}, usecols=["date", "close", "shares"]).drop_duplicates("date")
    raw.index = pd.to_datetime(raw["date"]); raw = raw.reindex(cal)
    rc = pd.to_numeric(raw["close"], errors="coerce").to_numpy(float)[idx]
    sh = pd.to_numeric(raw["shares"], errors="coerce").ffill().to_numpy(float)
    sh = np.where(sh > 0, sh, np.nan)[idx]
    tb = TR.one(sid, cal); trd, upo = np.asarray(tb["trd"], bool), np.asarray(tb["up_o"], bool)
    bad_day = np.zeros(n + 1, bool); bb = np.flatnonzero(nb[:m] == np.arange(m)); bad_day[idx[bb]] = True
    cbad = np.r_[0, np.cumsum(bad_day)]
    # 候選列：d 有效 K 棒、t ＝ 下一個交易日也有有效 K 棒且 eligible、d 在窗內
    a0 = int(cal.searchsorted(pd.Timestamp(SPAN[W["tag"]][0]))); a1 = int(cal.searchsorted(pd.Timestamp(SPAN[W["tag"]][1]), side="right")) - 1
    kk = np.arange(m - 1)
    ok = (idx[kk + 1] == idx[kk] + 1) & el[np.minimum(idx[kk] + 1, n - 1)] & (idx[kk] >= a0) & (idx[kk] <= a1) & (kk >= 250)
    K_ = kk[ok]
    if len(K_) == 0:
        return None
    # ── 價
    ma5, ma10, ma20, ma60, ma100 = (_roll(c, w, "mean") for w in (5, 10, 20, 60, 100))
    sd20 = pd.Series(c).rolling(20, min_periods=20).std(ddof=0).to_numpy()
    bu, bl = ma20 + 2 * sd20, ma20 - 2 * sd20
    bbw = (bu - bl) / ma20
    bbp = pd.Series(bbw).rolling(250, min_periods=250).apply(lambda x: (x[:-1] < x[-1]).mean(), raw=True).to_numpy()
    hi250, lo250 = _roll(c, 250, "max"), _roll(c, 250, "min")
    r_ = lambda w_: np.r_[np.full(w_, np.nan), c[w_:] / c[:-w_] - 1]
    amt20p = np.r_[np.nan, _roll(amt, 20, "mean")[:-1]]
    amt20 = _roll(amt, 20, "mean")
    amt120p = np.r_[np.full(20, np.nan), _roll(amt, 120, "mean")[:-20]]
    lu20 = _roll(up.astype(float), 20, "sum")
    K = kd(c, h, l); Kr = run_len(np.nan_to_num(K) > 80)
    R14, R6, R12 = rsi(c, 14), rsi(c, 6), rsi(c, 12)
    e20 = ema(c, 20); v2 = run_len(e20 > np.nan_to_num(ma20, nan=np.inf))
    mas = np.vstack([ma5, ma10, ma20])
    tang = np.full(m, np.nan)
    for i in range(40, m):
        blk = mas[:, i - 20:i]
        tang[i] = blk.max() / blk.min() - 1 if np.isfinite(blk).all() else np.nan
    mx60p = np.r_[np.nan, _roll(c, 60, "max")[:-1]]; mn60p = np.r_[np.nan, _roll(c, 60, "min")[:-1]]
    # V3 修正箱
    v3 = np.zeros(m, bool); last_touch = -1; box = np.nan; low_since = False
    for i in range(m):
        if last_touch >= 0 and i - last_touch - 1 >= 20 and low_since and c[i] > box:
            v3[i] = True
        if np.isfinite(bu[i]) and c[i] >= bu[i]:
            last_touch = i; box = h[i]; low_since = False
        elif np.isfinite(bl[i]) and c[i] <= bl[i]:
            low_since = True
    turn = vol / sh
    mcap = rc * sh
    R = {}
    R["v_r5"], R["v_r20"], R["v_r60"], R["v_r120"] = r_(5), r_(20), r_(60), r_(120)
    R["v_dhi"] = c / hi250 - 1; R["v_dlo"] = c / lo250 - 1
    R["f_bull"] = ((ma5 > ma20) & (ma20 > ma60) & (ma60 > ma100)).astype(float); R["f_ma100"] = (c > ma100).astype(float)
    R["l_lu20"] = np.minimum(lu20, 3)
    R["v_bbw"] = bbp
    R["v_ar"] = amt / amt20p; R["v_a20120"] = amt20 / amt120p; R["v_turn"] = turn
    R["v_mcap"] = mcap; R["v_shares"] = sh
    R["l_px"] = np.where(rc < 20, 0, np.where(rc < 50, 1, np.where(rc < 100, 2, 3))).astype(float)
    R["f_K1"] = (Kr >= 3).astype(float); R["l_K1"] = np.where(Kr == 0, 0, np.where(Kr <= 2, 1, np.where(Kr <= 5, 2, 3))).astype(float)
    R["f_K2"] = ((c > bu) & (amt >= 2 * amt20p)).astype(float)
    R["f_K3a"] = (R14 > 50).astype(float)
    R["f_K3b"] = np.r_[0.0, ((R6[:-1] <= R12[:-1]) & (R6[1:] > R12[1:])).astype(float)]
    R["f_K4"] = ((tang <= 0.02) & (c / o - 1 >= 0.04) & (c > ma20) & (c > ma100) & (amt >= 2 * amt20p)).astype(float)
    R["f_K5a"] = (turn >= 0.10).astype(float); R["f_K5b"] = (turn >= 0.20).astype(float)
    R["f_V1"] = ((mx60p / mn60p - 1 <= 0.25) & (np.r_[np.nan, amt20[:-1]] <= 0.7 * np.r_[np.nan, _roll(amt, 120, "mean")[:-1]]) & (c > mx60p) & (amt >= 2 * amt20p)).astype(float)
    R["l_V2"] = np.where(v2 == 0, 0, np.where(v2 <= 4, 1, np.where(v2 <= 9, 2, 3))).astype(float)
    R["f_V3"] = v3.astype(float)
    # NaN 保護：原值算不出的二元特徵 ⇒ NaN
    for k_, dep in (("f_bull", ma100), ("f_ma100", ma100), ("f_K2", amt20p), ("f_K3a", R14), ("f_K4", tang), ("f_V1", mx60p), ("f_K5a", turn), ("f_K5b", turn)):
        R[k_] = np.where(np.isfinite(dep), R[k_], np.nan)
    for k_ in ("f_K1", "l_K1"):
        R[k_] = np.where(np.isfinite(K), R[k_], np.nan)
    R["l_px"] = np.where(np.isfinite(rc), R["l_px"], np.nan)
    # ── 營收（最新可用期：生效日 ≤ d）
    pos_d = idx
    V = W["REV"][sid].to_numpy(float) if sid in W["REV"].columns else None
    for k_ in ("v_yoy", "v_mom", "v_streak", "v_d24", "f_R1", "f_R2a", "f_R2b", "f_revhi"):
        R[k_] = np.full(m, np.nan)
    if V is not None:
        eff = W["REV_EFF"]; pk = np.full(len(V), np.nan)
        yoy = np.full(len(V), np.nan); yoy[12:] = np.where((V[:-12] > 0) & np.isfinite(V[:-12]), V[12:] / V[:-12] - 1, np.nan)
        mom = np.full(len(V), np.nan); mom[1:] = np.where((V[:-1] > 0), V[1:] / V[:-1] - 1, np.nan)
        stk = np.zeros(len(V)); r0 = 0
        for j in range(len(V)):
            r0 = r0 + 1 if (np.isfinite(yoy[j]) and yoy[j] > 0) else 0; stk[j] = r0
        d24 = np.full(len(V), np.nan)
        for j in range(24, len(V)):
            hh = V[j - 24:j]; hh = hh[np.isfinite(hh)]
            if np.isfinite(V[j]) and len(hh) >= 18 and hh.max() > 0:
                d24[j] = V[j] / hh.max() - 1
        y3 = pd.Series(yoy).rolling(3, min_periods=3).mean().to_numpy()
        r1 = np.full(len(V), np.nan); r1[3:] = ((y3[3:] > 0) & (y3[:-3] <= 0)).astype(float); r1[3:][~(np.isfinite(y3[3:]) & np.isfinite(y3[:-3]))] = np.nan
        order = np.argsort(eff, kind="stable"); effs = eff[order]
        for i in range(m):
            j = int(np.searchsorted(effs, pos_d[i], side="right")) - 1
            if j < 0:
                continue
            kx = order[j]
            while kx >= 0 and not np.isfinite(V[kx]):
                kx -= 1
            if kx < 0:
                continue
            R["v_yoy"][i] = yoy[kx]; R["v_mom"][i] = mom[kx]; R["v_streak"][i] = stk[kx]; R["v_d24"][i] = d24[kx]; R["f_R1"][i] = r1[kx]
            R["f_R2a"][i] = float(yoy[kx] >= 0.5) if np.isfinite(yoy[kx]) else np.nan; R["f_R2b"][i] = float(yoy[kx] >= 1.0) if np.isfinite(yoy[kx]) else np.nan
    if sid in W["REVFLAG"].columns:
        fv = W["REVFLAG"][sid].to_numpy(float)[pos_d]
        R["f_revhi"] = np.where(np.isfinite(fv), (fv == 100).astype(float), np.nan)
    # ── 大盤
    R["f_mkt"] = W["MKT"][pos_d]
    # ── 主窗才有：財報、法人、融資、借券、注意處置
    for k_ in ("f_eps", "f_gm", "f_opm", "v_roe", "v_f5", "v_f20", "v_t5", "v_t20", "l_tstreak", "v_m20", "v_mu", "f_mstop", "v_sbl20", "l_att", "f_disp"):
        R[k_] = np.full(m, np.nan)
    if main:
        fr = W["FIN"].get(sid)
        if fr:
            fpos = np.array([x[0] for x in fr])
            for i in range(m):
                cj = np.flatnonzero(fpos <= pos_d[i])                     # 可用日不保證隨季單調 ⇒ 取「已可用」中最新的一季
                if len(cj) == 0:
                    continue
                j = int(cj[-1])
                _, y, q, eps, gm, opm, roe = fr[j]
                pv = fr[j - 1] if j >= 1 else None
                ly = next((x for x in fr[:j] if x[1] == y - 1 and x[2] == q), None)
                if pv is not None and (pv[1], pv[2]) == ((y, q - 1) if q > 1 else (y - 1, 4)):
                    R["f_eps"][i] = float(eps > 0 and pv[3] <= 0) if np.isfinite(eps) and np.isfinite(pv[3]) else np.nan
                    R["f_gm"][i] = float(gm > pv[4]) if np.isfinite(gm) and np.isfinite(pv[4]) else np.nan
                if ly is not None:
                    R["f_opm"][i] = float(opm > ly[5]) if np.isfinite(opm) and np.isfinite(ly[5]) else np.nan
                R["v_roe"][i] = roe
        p = os.path.join(W["data"], "stocks_inst", sid + ".csv")
        if os.path.exists(p):
            it = pd.read_csv(p, dtype={"date": str}, usecols=["date", "foreign", "trust"]).drop_duplicates("date", keep="last")
            it.index = pd.to_datetime(it["date"]); first = int(cal.searchsorted(it.index.min()))
            fo = pd.to_numeric(it["foreign"], errors="coerce").reindex(cal).fillna(0.0).to_numpy()
            tr = pd.to_numeric(it["trust"], errors="coerce").reindex(cal).fillna(0.0).to_numpy()
            okd = (pos_d - 19 >= first)
            for w_, kf, kt in ((5, "v_f5", "v_t5"), (20, "v_f20", "v_t20")):
                sf = pd.Series(fo).rolling(w_).sum().to_numpy()[pos_d]; stt = pd.Series(tr).rolling(w_).sum().to_numpy()[pos_d]
                R[kf] = np.where(okd, sf / sh, np.nan); R[kt] = np.where(okd, stt / sh, np.nan)
            ts_ = run_len(tr > 0)[pos_d]
            R["l_tstreak"] = np.where(pos_d >= first, np.where(ts_ == 0, 0, np.where(ts_ <= 2, 1, np.where(ts_ <= 5, 2, 3))), np.nan).astype(float)
        p = os.path.join(W["data"], "stocks_margin", sid + ".csv")
        if os.path.exists(p):
            mg = pd.read_csv(p, dtype={"date": str}, usecols=["date", "m_balance", "m_limit", "note"]).drop_duplicates("date", keep="last")
            mg.index = pd.to_datetime(mg["date"])
            mb = pd.to_numeric(mg["m_balance"], errors="coerce").reindex(cal).ffill().to_numpy()
            ml = pd.to_numeric(mg["m_limit"], errors="coerce").reindex(cal).ffill().to_numpy()
            nt = mg["note"].reindex(cal).fillna("").astype(str).to_numpy()
            has = mg["m_balance"].reindex(cal).notna().to_numpy()
            mbd = mb[pos_d]; mb20 = mb[np.maximum(pos_d - 20, 0)]
            R["v_m20"] = np.where(has[pos_d] & (pos_d >= 20), (mbd - mb20) * 1000 / sh, np.nan)
            R["v_mu"] = np.where(has[pos_d] & (ml[pos_d] > 0), mbd / ml[pos_d], np.nan)
            R["f_mstop"] = np.where(has[pos_d], np.array(["O" in x for x in nt[pos_d]], float), np.nan)
        sb = W["SBL"]["S"].get(sid)
        if sb is not None or True:
            ser = np.full(n, np.nan)
            if sb:
                ks = np.fromiter(sb.keys(), int); ser[ks] = np.fromiter(sb.values(), float)
            f0 = W["SBL"]["first"]
            ser = np.where(np.arange(n) >= f0, np.nan_to_num(ser, nan=0.0), np.nan)   # 不在當日借券檔 ⇒ 0（researchSBL 同讀法）
            R["v_sbl20"] = np.where(pos_d - 20 >= f0, (ser[pos_d] - ser[pos_d - 20]) / sh, np.nan)
        ad = W["ATT"].get(sid, np.zeros(0, int))
        cnt = np.searchsorted(ad, pos_d, side="right") - np.searchsorted(ad, pos_d - 59, side="left")
        a_first = int(cal.searchsorted(pd.Timestamp("2011-01-03")))
        R["l_att"] = np.where(pos_d - 59 >= a_first, np.where(cnt == 0, 0, np.where(cnt <= 2, 1, 2)), np.nan).astype(float)
        dsp = W["DISP"].get(sid, [])
        R["f_disp"] = np.array([float(any(a_ <= p_ and b_ >= p_ - 59 for a_, b_ in dsp)) for p_ in pos_d])
    # ── 結束特徵（researchSurgeEnd；寫死 2026-09-29 16:05 台北，未看任何數字前）
    body = c / o - 1; ushadow = h - np.maximum(o, c); pc = np.r_[np.nan, c[:-1]]
    R["f_E1"] = np.where(np.isfinite(amt20p), ((body <= -0.04) & (amt >= 2 * amt20p)).astype(float), np.nan)
    R["f_E2"] = np.where(np.isfinite(pc), ((ushadow >= 2 * np.abs(c - o)) & (ushadow / pc >= 0.03)).astype(float), np.nan)
    kr_prev = np.r_[0, Kr[:-1]]
    R["f_E3"] = np.where(np.isfinite(K), ((kr_prev >= 3) & (np.nan_to_num(K) <= 80)).astype(float), np.nan)
    for nm_, mav in (("f_E4", ma10), ("f_E5", ma20)):
        pm = np.r_[np.nan, mav[:-1]]
        R[nm_] = np.where(np.isfinite(pm), ((c < mav) & (pc >= pm)).astype(float), np.nan)
    R["f_E7"] = np.full(m, np.nan); R["f_E8"] = np.full(m, np.nan)
    if main:
        ad_ = W["ATT"].get(sid, np.zeros(0, int))
        c5 = np.searchsorted(ad_, pos_d, side="right") - np.searchsorted(ad_, pos_d - 4, side="left")
        dsp_ = W["DISP"].get(sid, [])
        inD = np.array([any(a_ <= p_ <= b_ for a_, b_ in dsp_) for p_ in pos_d])
        a_first = int(cal.searchsorted(pd.Timestamp("2011-01-03")))
        R["f_E7"] = np.where(pos_d - 4 >= a_first, ((c5 > 0) | inD).astype(float), np.nan)
        p = os.path.join(W["data"], "stocks_inst", sid + ".csv")
        if os.path.exists(p):
            it = pd.read_csv(p, dtype={"date": str}, usecols=["date", "foreign", "trust"]).drop_duplicates("date", keep="last")
            it.index = pd.to_datetime(it["date"]); first = int(cal.searchsorted(it.index.min()))
            ft = (pd.to_numeric(it["foreign"], errors="coerce") + pd.to_numeric(it["trust"], errors="coerce")).reindex(cal).fillna(0.0).to_numpy()
            s5 = pd.Series(ft).rolling(5).sum().to_numpy(); s20p = np.r_[np.full(5, np.nan), pd.Series(ft).rolling(20).sum().to_numpy()[:-5]]
            R["f_E8"] = np.where(pos_d - 24 >= first, ((s5[pos_d] < 0) & (s20p[pos_d] > 0)).astype(float), np.nan)
    R["px_c"] = cff[pos_d]
    R["px_on"] = np.where(pos_d + 1 <= n - 1, ofull[np.minimum(pos_d + 1, n - 1)], np.nan)
    # ── 標籤與後續報酬（日曆位置）
    out = {"d": pos_d[K_].astype(np.int32)}
    for k_, v in R.items():
        out[k_] = np.asarray(v, float)[K_].astype(np.float32)
    t = pos_d[K_] + 1
    lab = {}
    for F, (H, g) in FDEF.items():
        y = np.full(len(t), np.nan)
        okw = (t + H <= n - 1)
        te = np.minimum(t + H, n - 1)
        clean = (cbad[te + 1] - cbad[t + 1]) == 0
        mx = np.array([cff[a + 1:b + 1].max() if b > a else np.nan for a, b in zip(t, te)])
        q = okw & clean & (mx >= cff[t] * (1 + g))
        y[okw & clean] = 0.0
        last = -10 ** 9
        for i in np.flatnonzero(q):
            if t[i] - last > H:
                y[i] = 1.0; last = t[i]
        # 同一檔：成立事件後 H 日內再成立 ⇒ 0（已是 0）
        lab[F] = y
        if F == "F1":
            yao = np.full(len(t), np.nan)
            ev = {k_: np.full(len(t), np.nan) for k_ in ("P", "dP", "e20", "e50", "rP20", "rP60", "retP")}
            for i in np.flatnonzero(y == 1):
                seg = cff[t[i] + 1:te[i] + 1]; p_ = t[i] + 1 + int(np.argmax(seg)); pk = cff[p_]
                if p_ + 60 <= n - 1 and cbad[p_ + 61] - cbad[p_ + 1] == 0:
                    yao[i] = float(cff[p_ + 1:p_ + 61].min() <= pk * 0.5)
                # 結束（researchSurgeEnd 寫死）：高點 P 之後 250 日內第一次收盤 ≤ 高點×0.8／×0.5；跨資料尾或壞根 ⇒ NaN
                ev["P"][i] = p_; ev["dP"][i] = p_ - t[i]
                ev["retP"][i] = pk / ofull[t[i]] - 1 if (np.isfinite(ofull[t[i]]) and ofull[t[i]] > 0) else np.nan
                wend = min(p_ + 250, n - 1); cleanw = cbad[wend + 1] - cbad[p_ + 1] == 0
                if cleanw:
                    after = cff[p_ + 1:wend + 1]
                    for thr, kk_ in ((0.8, "e20"), (0.5, "e50")):
                        hit = np.flatnonzero(after <= pk * thr)
                        if len(hit):
                            ev[kk_][i] = hit[0] + 1
                        elif p_ + 250 <= n - 1:
                            ev[kk_][i] = np.inf                       # 250 日內沒發生
                for hh_, kk_ in ((20, "rP20"), (60, "rP60")):
                    if p_ + hh_ <= n - 1 and cbad[p_ + hh_ + 1] - cbad[p_ + 1] == 0:
                        ev[kk_][i] = cff[p_ + hh_] / pk - 1
            lab["yao"] = yao
            for k_, v_ in ev.items():
                lab["ev_" + k_] = v_
    for k_, v in lab.items():
        out[f"y_{k_}"] = v.astype(np.float32)
    k_of = np.full(n, -1); k_of[idx] = np.arange(m)
    buy = trd[np.minimum(t, n - 1)] & np.isfinite(ofull[np.minimum(t, n - 1)]) & (ofull[np.minimum(t, n - 1)] > 0) & ~upo[np.minimum(t, n - 1)]
    r20 = AV.r20_cal(cfull, idx)[pos_d[K_]]
    out["r20c"] = r20.astype(np.float32)
    for hh in HS:
        x = pos_d[K_] + hh
        okh = buy & (x <= n - 1)
        x2 = np.minimum(x, n - 1)
        kx = np.searchsorted(idx, x2, side="right") - 1
        clean = nb[np.maximum(K_ - 19, 0)] > kx
        rr = np.where(okh & clean, cff[x2] / ofull[np.minimum(t, n - 1)] - 1, np.nan)
        out[f"R{hh}"] = rr.astype(np.float32)
    out["ind"] = np.full(len(K_), -1, np.int16)
    code = W["IND"].get(sid)
    if code is not None and str(code).isdigit():
        out["ind"][:] = int(code)
    return sid, out


def table(W, procs=2, log=print):
    with Pool(procs, initializer=_init, initargs=(W,)) as pool:
        res = [r for r in pool.imap_unordered(stock, W["sids"], chunksize=8) if r is not None]
    parts = []
    for sid, o in res:
        d = pd.DataFrame(o); d.insert(0, "sid", sid); parts.append(d)
    T = pd.concat(parts, ignore_index=True).sort_values(["d", "sid"]).reset_index(drop=True)
    T["月"] = np.array([str(x)[:7] for x in W["cal"][T["d"].to_numpy()]])
    log(f"[{W['tag']} 特徵表] {len(T):,} 股-日｜{T['sid'].nunique()} 檔")
    return T


def q5(v):
    """一天的橫斷面五等分（1 低～5 高）；avgdown.deciles 同式（同值依陣列序 ＝ 代號序）。"""
    out = np.full(len(v), np.nan); ok = np.flatnonzero(np.isfinite(v)); k = len(ok)
    if k == 0:
        return out
    order = ok[np.lexsort((ok, v[ok]))]
    out[order] = (np.arange(k) * 5) // k + 1
    return out


def cross(T, W, log=print):
    """五等分、產業排名（產業 20 日報酬 ＝ 當日母體同產業 20 日報酬平均，產業間排名再五等分到個股）、基準② X。"""
    qcols = [f[3] for f in FEATS if f[2] == "q5" and f[3] != "v_indrk"]
    gi = T.groupby("d").indices
    Q = {c: np.full(len(T), np.nan) for c in qcols}
    ir = np.full(len(T), np.nan)
    X = {hh: np.full(len(T), np.nan) for hh in HS}
    r20 = T["v_r20"].to_numpy(float); ind = T["ind"].to_numpy()
    rc = T["r20c"].to_numpy(float)
    RR_ = {hh: T[f"R{hh}"].to_numpy(float) for hh in HS}
    V = {c: T[c].to_numpy(float) for c in qcols}
    for d, ix in gi.items():
        ix = np.asarray(ix)
        for c in qcols:
            Q[c][ix] = q5(V[c][ix])
        # 產業
        rr = r20[ix]; ii = ind[ix]; okk = np.isfinite(rr) & (ii >= 0)
        if okk.sum() > 0:
            s_ = pd.Series(rr[okk]).groupby(ii[okk]).mean()
            s_ = s_[pd.Series(ii[okk]).value_counts().reindex(s_.index) >= 3]
            if len(s_) >= 5:
                rk = q5(s_.to_numpy())
                mp = dict(zip(s_.index, rk))
                ir[ix] = np.array([mp.get(z, np.nan) for z in ii])
        # 基準②
        for hh in HS:
            y = RR_[hh][ix]; r = rc[ix]; okb = np.isfinite(y) & np.isfinite(r)
            if okb.sum() < 20:
                continue
            j = np.flatnonzero(okb); dcl = AV.deciles(np.where(okb, r, np.nan))[j]; yy = y[j]
            sm = np.bincount(dcl, weights=yy, minlength=10); ct = np.bincount(dcl, minlength=10); co = ct[dcl] - 1
            X[hh][ix[j]] = np.where(co > 0, yy - (sm[dcl] - yy) / np.maximum(co, 1), np.nan)
    for c in qcols:
        T["q_" + c] = Q[c].astype(np.float32)
    T["q_v_indrk"] = ir.astype(np.float32)
    for hh in HS:
        T[f"X{hh}"] = X[hh].astype(np.float32)
    log(f"[{W['tag']} 橫斷面] 完成")
    return T


def tdcc_feature(T, W, log=print):
    """集保 400 張以上大戶持股比例 4 週變化（主窗；連續序列 2019 起）。需要 parquet 讀取套件；沒有 ⇒ 回 None（照實剔除）。
    400 張以上 ＝ tdcc.level_of(tdcc_levels, 400_001) 的下限級起（資料庫 1453：超過 400 張 ＝ 第 12 級起、唯一解）；⛔ 不自己寫級數
    觀察日 d 用「資料日期 ＜ d」的最新一週（集保週五資料、次一交易日起可得）與其前 4 週（同檔週序列往前第 4 筆）"""
    try:
        import pyarrow  # noqa: F401
    except ImportError:
        log("[集保] 沒有 pyarrow ⇒ 剔除"); return None
    # tdcc.py（資料庫 repo 根目錄，git show 同一 sha）import 了本機沒有的 repo 模組 ⇒ 只把 level_of 這一個函式原文抽出來執行（⛔ 不改寫、不自寫級數）
    import ast
    src = open(os.path.join(os.path.dirname(W["data"]), "tdcc.py"), encoding="utf-8").read()
    fn = next(nd for nd in ast.parse(src).body if isinstance(nd, ast.FunctionDef) and nd.name == "level_of")
    ns = {}; exec(compile(ast.Module(body=[fn], type_ignores=[]), "tdcc.py:level_of", "exec"), ns)
    lv = pd.read_csv(os.path.join(W["data"], "meta", "tdcc_levels.csv"))
    rows = [(int(r.level), int(r.lower_lo), int(r.lower_hi), int(r.upper_lo), int(r.upper_hi)) for r in lv.itertuples()]
    lo, hi = ns["level_of"](rows, 400_001)
    assert lo == hi, (lo, hi)
    parts = []
    for f in sorted(glob.glob(os.path.join(W["data"], "tdcc_hist", "*.parquet"))):
        x = pd.read_parquet(f, columns=["date", "stock_id", "level", "pct"])
        parts.append(x[x["level"].astype(int).between(lo, 15)])
    for f in sorted(glob.glob(os.path.join(W["data"], "tdcc", "*.csv"))):
        x = pd.read_csv(f, dtype={"stock_id": str}, usecols=["date", "stock_id", "level", "pct"])
        parts.append(x[x["level"].astype(int).between(lo, 15)])
    A = pd.concat(parts); A["date"] = pd.to_datetime(A["date"]); A["stock_id"] = A["stock_id"].astype(str)
    A = A.drop_duplicates(["date", "stock_id", "level"], keep="last").groupby(["stock_id", "date"])["pct"].sum().reset_index().sort_values(["stock_id", "date"])
    A = A[A["date"] >= pd.Timestamp("2019-01-01")]
    A["chg4"] = A.groupby("stock_id")["pct"].diff(4)
    cal = W["cal"]; out = np.full(len(T), np.nan)
    by = {s: (g["date"].to_numpy(), g["chg4"].to_numpy(float)) for s, g in A.groupby("stock_id")}
    dd = cal[T["d"].to_numpy()].to_numpy()
    for s, ix in T.groupby("sid").indices.items():
        if s not in by:
            continue
        ds, ch = by[s]; j = np.searchsorted(ds, dd[ix], side="left") - 1
        ok = j >= 0; v = np.full(len(ix), np.nan); v[ok] = ch[j[ok]]; out[ix] = v
    log(f"[集保] 400 張以上 ＝ 第 {lo} 級起（tdcc.level_of）｜有值股-日 {int(np.isfinite(out).sum()):,}")
    return out


def level_col(f):
    """特徵 ⇒ (欄名, 可取值 list)。"""
    name, cat, kind, col = f[:4]
    if kind == "bin":
        return col, [1.0]
    if kind == "q5":
        return "q_" + col, [1.0, 2.0, 3.0, 4.0, 5.0]
    return col, sorted(LVL[col])

# -*- coding: utf-8 -*-
"""USREG-C4（← 草稿 B4，sha 20479c52532466ba）剔除股反彈：被主動踢出 S&P 500／400 的股票之後會贏大盤嗎？
裁定 seq321 §三：N（美股帳）2（甲 事件層、乙 組合層）；判定照登錄；與 A4-7（指數成分剔除，已結案）分開計 N、結果句並引；⛔ 不取代、⛔ 不退 N。
資料庫 data/membership/removals_analysis.csv（b33bde6）：reason_cat_norm、determined；只有生效日、⛔ 沒有公告日 ⇒ 公告日臂拿掉（登錄 §二 描述項），照寫。

═══ C4 補讀法（C4- 標；⭐ 寫死於 2026-10-10 23:36（台北），寫死前 ⛔ 沒看任何 C4 數字）═══
 C4-1 事件 ＝ removals_analysis.csv 中 reason_cat_norm ＝ index_change 且 index_change_sub ∈ {removed_or_demoted（S&P 400 踢出／降 600）、
      demoted（S&P 500 降級、非到 400）、demoted_to_sp400（S&P 500 → 400）}；⛔ 不含 promoted_to_sp500（升級）與 acquired／spinoff／renamed／failed／other。
      主結果只用 determined ＝ 1；determined ＝ 0（暫定分類）加入的版本只描述。生效日 2016-01-04 ～ 2025-09-30。
 C4-2 價格 ＝ A3 快取（~/us_work/a3/stocks.pkl：還原 OHLC、有效 K 棒、硬斷點；881c86a 聯集轉接層，移出指數後的列照轉接層 D3③ 保留）；
      「≥ 5 美元」＝ 生效日前一個有效交易日的原始收盤（A4 world RCu：Yahoo close × 日後拆股比）。代號不在價格面板 ⇒ 計「無價格」。
 C4-3 甲（判定）：生效日（≥ 該日的第一個交易日 pE）次一交易日 b 開盤進，252 個交易日（b＋251 收盤）報酬 − ^SP500TR 同段（b 開盤 → b＋251 收盤；
      ^SP500TR 開盤 ＝ ^GSPC 開 × 同日 TR÷GSPC，A1 D2）；b 沒有有效開盤 ⇒ 往後找 5 根內第一個有效開盤，找不到 ⇒ 無價格。
      持有期碰到硬斷點 ⇒ 剔除（計數）；期間下市 ⇒ 用最後收盤（ffill）＝ 之後當現金 0 報酬（計數）；b＋251 超過 2026-09-30 ⇒ 不進該期（計數）。
      判：平均 ＞ 0 且月分群（b 的曆月）95% CI 不含 0 ⇒「被踢的股票之後贏大盤」（researchM.summ／verdict；n、n_eff ≥ 30）。N_前段 ＋1。
      描述：20、60、120 日；504 日（24 個月）、1260 日（60 個月）（覆蓋不足照報）；只 S&P 500 剔除、只 S&P 400 剔除。
 C4-4 對照（描述）：① 同期新加入：changes.csv（兩指數）的 added_ticker，同窗、同式 252 日超額；
      ②「跌深」對照：同一天（pE−1）同指數成分（未被剔除）中，前 12 個月報酬（pE−1 收盤 ÷ 252 根前收盤 − 1）同十分位的股票，同 b、同 252 日報酬平均 ⇒ 事件 − 對照。
      被踢前 12 個月報酬分佈（中位、p10、p90、對同指數中位）。
 C4-5 假訊號（描述）：甲 ＝ 每個事件換成「同一天、同指數、未被剔除」的隨機成分股（同 b、同 252 日）1,000 次 ⇒ 平均超額分佈，p ＝ 隨機平均 ≥ 實際的比例；
      乙 ＝ 同進場日、同持有天數的隨機成分股 200 次（每次一顆抽籤種子）⇒ 年化贏 ^SP500TR 的比例 p；p ≥ 5% ⇒ 結果句前加「隨機挑也有 x%」。
      rng ＝ default_rng([20261010, 4, 臂, r])。
 C4-6 乙（判定，組合層）：b 開盤進；8 槽等權；同日超額抽籤（102000＋r、200 顆）；research11.simulate_mtm（A3 core pf_run 同一套：tradable＋delist）。
      出場（seq308 條件出場、⛔ 無最長天數）：該股重新被加回較高指數 ⇒ 該加回日 d 的次一交易日開盤賣（從 S&P 500 被踢 ⇒ 回到 S&P 500；從 S&P 400 被踢 ⇒ 回到 S&P 400 或 500）；
      被併購下市 ⇒ 引擎 delist 規則（最後成交價結算）；窗尾 2026-09-30 收盤結算。持有期碰到硬斷點 ⇒ 該訊號剔除（W1b W5、A4 G11）。
      判準 ^SP500TR 同窗（K2；窗 ＝ 第一個進場日前一日收盤 ～ 2026-09-30）。成本 0.05%（敏感度 0.02、0.10、0.20%）。
      描述：固定 {20,60,120,240} 日（seq308）、NIXT 式「抱 5 年」（1260 日，窗內抱不滿照實）。
      必報：持有天數分佈、出場原因占比（升回指數／下市／窗尾）、每年換手、窗尾仍持有、離頂多近、等效獨立檔數（K6，抽籤種子 102000 的持股）。
 C4-7 必報：每年事件數（分 S&P 500、S&P 400）、排除的併購等件數、被踢後價格覆蓋率（12、24、60 個月；本快取實際可算比例＋資料庫 has_price 欄）；
      ⚠ 覆蓋率 ＜ 95% ⇒ 結果偏樂觀（缺價者多半後來下市）。
 C4-8 相鄰件並引：A4-7（resultsUSA34/A4/A4-7.json 成分剔除）不合格；已結案、⛔ 不取代、⛔ 不退 N。
 C4-9 先驗對錯（登錄 §六）：甲 平均 ＞ 0（約七成）；甲 測得出（約四成五）；效果量 ＜ 文獻 20 點（約八成）；扣跌深對照後剩一半以下（約五成五）；乙 合格或另列（約三成五）。
"""
from __future__ import annotations

import json
import os
import time

import numpy as np
import pandas as pd

from backtest import researchUSC as K

READ_TS = "2026-10-10 23:36（台北）"
SUBS = ("removed_or_demoted", "demoted", "demoted_to_sp400")
HS = (20, 60, 120, 252, 504, 1260)
W0, W1 = pd.Timestamp("2016-01-04"), pd.Timestamp("2025-09-30")


def load_events():
    d = pd.read_csv(K.p_new("membership", "removals_analysis.csv"), dtype={"removed_ticker": str})
    d["date"] = pd.to_datetime(d["date"])
    win = d[(d["date"] >= W0) & (d["date"] <= W1)].copy()
    ev = win[(win["reason_cat_norm"] == "index_change") & win["index_change_sub"].isin(SUBS)].copy()
    excl = win[~((win["reason_cat_norm"] == "index_change") & win["index_change_sub"].isin(SUBS))]
    return ev, excl, win


def load_adds():
    out = []
    for f, idx in (("membership", "sp500"), ("membership_sp400", "sp400")):
        c = pd.read_csv(K.p_new(f, "changes.csv"), dtype=str)
        c["date"] = pd.to_datetime(c["date"])
        c = c[(c["date"] >= W0) & (c["date"] <= W1) & c["added_ticker"].notna() & (c["added_ticker"] != "")]
        for r in c.itertuples():
            out.append((r.added_ticker, r.date, idx))
    return pd.DataFrame(out, columns=["ticker", "date", "index"])


class Px:
    def __init__(self):
        from backtest import researchUSA3_core as C
        from backtest import researchUSA1_data as A
        self.C = C
        meta, ST = C.load_cache()
        self.meta, self.ST = meta, ST
        self.cal = meta["cal"]; self.n = len(self.cal); self.w1 = meta["w1"]
        self.sids = sorted(ST)
        M = A.load_market()
        cs = pd.to_datetime(pd.Series(M["cal"]))
        self.TRc = pd.Series(M["C"]["TR"], index=cs).reindex(self.cal).ffill().to_numpy()
        self.TRo = pd.Series(M["O"]["TR"], index=cs).reindex(self.cal).to_numpy()
        R = K.rworld(); Wd = R["Wd"]
        self.RCu = {str(t): Wd["RCu"][:, j] for t, j in Wd["ix"].items()}
        self.cpb = {s: np.r_[0, np.cumsum(ST[s]["pb"])] for s in self.sids}
        self.lastv = {s: int(np.flatnonzero(ST[s]["valid"])[-1]) for s in self.sids}
        self.M5 = np.column_stack([ST[s]["m5"] for s in self.sids]); self.M4 = np.column_stack([ST[s]["m4"] for s in self.sids])
        self.CF = np.column_stack([ST[s]["closes"] for s in self.sids])
        self.ix = {s: i for i, s in enumerate(self.sids)}

    def entry(self, s, pE):
        d = self.ST[s]; o = d["opens"]
        for b in range(pE + 1, min(pE + 6, self.n)):
            if np.isfinite(o[b]) and o[b] > 0:
                return b
        return None

    def ret(self, s, b, H):
        """→ (超額, 報酬, 狀態)。"""
        x = b + H - 1
        if x > self.w1:
            return np.nan, np.nan, "超窗"
        d = self.ST[s]; cpb = self.cpb[s]
        if cpb[x + 1] - cpb[b + 1] > 0:
            return np.nan, np.nan, "斷點"
        r = d["closes"][x] / d["opens"][b] - 1
        rb = self.TRc[x] / self.TRo[b] - 1
        st = "下市" if self.lastv[s] < x else "ok"
        return r - rb, r, st

    def prior12(self, s, pE):
        d = self.ST[s]; a, b = pE - 1 - 251, pE - 1
        if a < 0 or not d["valid"][max(b - 4, 0):b + 1].any() or not d["valid"][max(a - 4, 0):a + 1].any():
            return np.nan
        if self.cpb[s][b + 1] - self.cpb[s][a + 1] > 0:
            return np.nan
        return d["closes"][b] / d["closes"][a] - 1


def run(a):
    T0 = time.time()
    ev, excl, win = load_events()
    P = Px(); cal = P.cal; C = P.C
    A4 = K.rworld()["A4"]
    # ── 事件表 ──
    rows = []
    for r in ev.itertuples():
        s = r.removed_ticker; pE = int(cal.searchsorted(r.date))
        rec = {"index": r.index, "date": r.date, "ticker": s, "sub": r.index_change_sub, "determined": int(r.determined), "pE": pE,
               "db12": r.has_price_12m, "db24": r.has_price_24m, "db60": r.has_price_60m}
        if s not in P.ST:
            rec["狀態"] = "無價格"; rows.append(rec); continue
        rc = P.RCu.get(s)
        vb = np.flatnonzero(P.ST[s]["valid"][:pE])
        px = rc[vb[-1]] if (rc is not None and len(vb)) else np.nan
        rec["前一日原始收盤"] = px
        if not (np.isfinite(px)):
            rec["狀態"] = "無價格"; rows.append(rec); continue
        if px < 5:
            rec["狀態"] = "<5美元"; rows.append(rec); continue
        b = P.entry(s, pE)
        if b is None:
            rec["狀態"] = "無價格"; rows.append(rec); continue
        rec["b"] = b; rec["狀態"] = "ok"
        for H in HS:
            ex, rr, stt = P.ret(s, b, H)
            rec[f"ex{H}"] = ex; rec[f"r{H}"] = rr; rec[f"st{H}"] = stt
        rec["prior12"] = P.prior12(s, pE)
        rows.append(rec)
    E = pd.DataFrame(rows)
    E["年"] = E["date"].dt.year
    ok = E["狀態"] == "ok"
    Em = E[ok & (E["determined"] == 1)].copy(); Em["b"] = Em["b"].astype(int)
    K.log("[C4] 事件 %d（主 %d）%.0fs" % (len(E), len(Em), time.time() - T0), "c4.log")

    def ev_stat(df, H=252):
        x = df[f"ex{H}"].to_numpy(float); T = df["b"].to_numpy(int)
        m = np.isfinite(x)
        if m.sum() == 0:
            return {"n": 0}
        s = A4.ev_summ(x[m], T[m], cal, 0)
        s["判語"] = s.get("判語", "—")
        return {k: s.get(k) for k in ("n", "平均", "中位", "勝率", "lo", "hi", "曆月數", "n_eff", "出口", "判語", "p10", "p90")}
    J = {"主（determined＝1）": ev_stat(Em)}
    for g, idx in (("只S&P500剔除", "sp500"), ("只S&P400剔除", "sp400")):
        J[g] = ev_stat(Em[Em["index"] == idx])
    J["含 determined＝0（描述）"] = ev_stat(E[ok])
    HD = {f"{H}日": ev_stat(Em, H) for H in HS if H != 252}
    for H in (252, 504, 1260):
        x = Em[f"ex{H}"]
        HD.setdefault(f"{H}日", {})["可算比例"] = float(x.notna().mean())
    # ── 對照 ──
    AD = load_adds(); arows = []
    for r in AD.itertuples():
        s = r.ticker
        if s not in P.ST:
            continue
        pE = int(cal.searchsorted(r.date)); b = P.entry(s, pE)
        if b is None:
            continue
        ex, rr, stt = P.ret(s, b, 252)
        arows.append({"b": b, "ex252": ex, "index": r.index})
    ADf = pd.DataFrame(arows)
    CT = {"同期新加入（252 日超額）": ev_stat(ADf) if len(ADf) else {"n": 0}}
    # 跌深對照
    removed_any = set(E["ticker"])
    dlt, pri_rel = [], []
    for r in Em.itertuples():
        pE = r.pE; b = r.b
        Mx = P.M5 if r.index == "sp500" else P.M4
        mem = np.flatnonzero(Mx[pE - 1])
        pr = np.array([P.prior12(P.sids[i], pE) for i in mem])
        okm = np.isfinite(pr)
        if okm.sum() < 20 or not np.isfinite(r.prior12):
            continue
        q = np.quantile(pr[okm], np.linspace(0, 1, 11))
        dec = min(9, int(np.searchsorted(q, r.prior12, side="right") - 1)); dec = max(dec, 0)
        pri_rel.append(r.prior12 - np.median(pr[okm]))
        same = [P.sids[i] for i, v, o_ in zip(mem, pr, okm) if o_ and P.sids[i] not in removed_any and q[dec] <= v <= q[dec + 1]]
        cr = []
        for s2 in same:
            o2 = P.ST[s2]["opens"][b]
            if not (np.isfinite(o2) and o2 > 0):
                continue
            ex2, rr2, st2 = P.ret(s2, b, 252)
            if np.isfinite(rr2):
                cr.append(rr2)
        if len(cr) >= 3 and np.isfinite(r.r252):
            dlt.append((r.b, r.r252 - float(np.mean(cr))))
    if dlt:
        dd = np.array(dlt); s = A4.ev_summ(dd[:, 1], dd[:, 0].astype(int), cal, 0)
        CT["跌深對照（事件 − 同十分位）"] = {k: s.get(k) for k in ("n", "平均", "中位", "lo", "hi", "判語")}
    pr12 = Em["prior12"].dropna()
    CT["被踢前12月報酬"] = {"中位": float(pr12.median()), "p10": float(pr12.quantile(0.1)), "p90": float(pr12.quantile(0.9)),
                       "對同指數中位的差（中位）": float(np.median(pri_rel)) if pri_rel else None}
    K.log("[C4] 對照 %.0fs" % (time.time() - T0), "c4.log")
    # ── 假訊號 甲 ──
    rng = np.random.default_rng([20261010, 4, 1, 0])
    pools = []
    for r in Em[np.isfinite(Em["ex252"])].itertuples():
        Mx = P.M5 if r.index == "sp500" else P.M4
        mem = [P.sids[i] for i in np.flatnonzero(Mx[r.pE - 1]) if P.sids[i] not in removed_any]
        vals = []
        for s2 in mem:
            o2 = P.ST[s2]["opens"][r.b]
            if np.isfinite(o2) and o2 > 0:
                ex2, _, _ = P.ret(s2, r.b, 252)
                if np.isfinite(ex2):
                    vals.append(ex2)
        pools.append(np.array(vals))
    real = float(np.nanmean(Em["ex252"]))
    sims = np.array([np.mean([p[rng.integers(len(p))] for p in pools if len(p)]) for _ in range(1000)])
    FKa = {"次數": 1000, "隨機平均超額中位": float(np.median(sims)), "p（隨機平均 ≥ 實際）": float(np.mean(sims >= real)), "實際平均": real}
    K.log("[C4] 假訊號甲 %.0fs" % (time.time() - T0), "c4.log")
    # ── 乙 組合層 ──
    sids = P.sids; w1 = P.w1
    trad, dl = C.pf_setup(P.ST, sids, cal, P.meta["w0"], w1)
    sig_rows = []; why = {"升回": 0, "窗尾": 0, "斷點剔除": 0}
    for r in Em.itertuples():
        s = r.ticker; e = int(r.b); d = P.ST[s]
        back = (d["m5"] if r.index == "sp500" else (d["m5"] | d["m4"]))
        xd = np.flatnonzero(back & (np.arange(P.n) > r.pE))
        x, endh = C.exit_after(xd, e, w1)
        if P.cpb[s][x + 1] - P.cpb[s][e + 1] > 0:
            why["斷點剔除"] += 1; continue
        why["升回" if not endh else "窗尾"] += 1
        sig_rows.append({"sid": s, "entry_pos": e, "xpos": x, "g": C.gross_exit(d, e, x, endh), "endhold": endh})
    t0 = min(r["entry_pos"] for r in sig_rows); a0 = t0 - 1
    bref = C.bench_row(cal, a0, w1)
    sig, endh, xp = C.pf_sig(sig_rows)
    arms = {"main": {"sig": sig, "endhold": endh, "xp": xp, "seg": (a0, w1)}}
    for c_ in (0.0002, 0.0010, 0.0020):
        arms[f"cost{c_}"] = {"sig": sig, "endhold": endh, "xp": xp, "seg": (a0, w1), "cost": c_}
    for H in K.FIXH + (1260,):
        fr = C.fixed_rows(sig_rows, H, w1, {s: P.ST[s]["closes"] for s in sids}, {s: P.ST[s]["opens"] for s in sids})
        sg2, eh2, xp2 = C.pf_sig(fr)
        arms[f"fix{H}"] = {"sig": sg2, "endhold": eh2, "xp": xp2, "seg": (a0, w1)}
    res = C.pf_run(arms, procs=a.procs, nseed=a.seeds)
    PF = {k: C.pf_agg(v, bref) for k, v in res.items()}
    # 出場原因占比（以訊號計；下市由引擎結算 ⇒ 用 delist_settled 中位另報）
    PF["main"]["出場原因（訊號）"] = why
    PF["main"]["下市結算筆數（逐種子中位）"] = float(np.median([x["delist_settled"] or 0 for x in res["main"]]))
    # 等效獨立檔數：種子 102000 的持股（重跑一次取 audit）
    from backtest import research11 as R11
    aud = []
    R11.simulate_mtm(sig, C.RULE, K.N_SLOTS, np.random.default_rng(K.SEED0), {s: P.ST[s]["closes"] for s in sids}, {s: P.ST[s]["opens"] for s in sids},
                     P.n, return_equity=True, pick=None, d_max=None, queue_days=0, cash_mode="zero", tradable=trad, delist=dl, audit=aud)
    Wd = K.rworld()["Wd"]; wix = {str(t): j for t, j in Wd["ix"].items()}
    held = {}; cur = set()
    for x_ in sorted(aud, key=lambda z: (z["t"], z["side"] != "sell")):
        if x_["side"] == "buy":
            cur.add(x_["sid"])
        elif x_["side"] == "sell":
            cur.discard(x_["sid"])
        held[int(x_["t"])] = sorted(wix[s] for s in cur if s in wix)
    ms = K.rworld()["ms"]; hm = {}
    keys = sorted(held)
    for m_ in ms:
        if m_ < t0 or m_ > w1:
            continue
        i = np.searchsorted(keys, m_, side="right") - 1
        if i >= 0:
            hm[int(m_)] = held[keys[i]]
    PF["main"]["等效獨立檔數"] = K.n_eff(Wd, hm)
    # 假訊號 乙
    ent = {}
    for r in Em.itertuples():
        Mx = P.M5 if r.index == "sp500" else P.M4
        ent[r.b] = [P.sids[i] for i in np.flatnonzero(Mx[r.pE - 1]) if P.sids[i] not in removed_any]
    farms = {}
    for rr in range(a.seeds):
        g = np.random.default_rng([20261010, 4, 2, rr]); fr = []
        for x_ in sig_rows:
            e = x_["entry_pos"]; H = x_["xpos"] - e
            pool = ent.get(e, [])
            for _ in range(20):
                s2 = pool[g.integers(len(pool))] if pool else None
                if s2 is None:
                    break
                o2 = P.ST[s2]["opens"][e]
                if np.isfinite(o2) and o2 > 0 and P.cpb[s2][min(e + H, P.n - 1) + 1] - P.cpb[s2][e + 1] == 0:
                    x2 = min(e + H, w1); eh = (e + H) >= w1
                    fr.append({"sid": s2, "entry_pos": e, "xpos": x2, "g": C.gross_exit(P.ST[s2], e, x2, eh), "endhold": eh}); break
        sg3, eh3, xp3 = C.pf_sig(fr)
        farms[f"fake{rr}"] = {"sig": sg3, "endhold": eh3, "xp": xp3, "seg": (a0, w1)}
    resf = C.pf_run(farms, procs=a.procs, nseed=1)
    fc = np.array([v[0]["cagr"] for v in resf.values()])
    FKb = {"次數": int(len(fc)), "隨機年化中位": float(np.median(fc)), "p（隨機年化 ＞ ^SP500TR）": float(np.mean(fc > bref["年化"])),
           "隨機年化 ≥ 主臂中位 的比例": float(np.mean(fc >= PF["main"]["年化中位"]))}
    K.log("[C4] 組合層 %.0fs" % (time.time() - T0), "c4.log")
    # ── 必報：每年事件數、排除、覆蓋 ──
    yr = E[E["determined"] == 1].groupby(["年", "index"]).size().unstack(fill_value=0)
    exc = excl.groupby(["index", "reason_cat_norm", "index_change_sub"], dropna=False).size()
    cov = {}
    for H, db in ((252, "db12"), (504, "db24"), (1260, "db60")):
        base = E[E["determined"] == 1]
        cov[f"{H}日"] = {"本快取可算比例（主事件）": float(base[f"ex{H}"].notna().mean()) if f"ex{H}" in base else None,
                        "資料庫 has_price 比例（主事件，NA 不計）": float(pd.to_numeric(base[db], errors="coerce").dropna().mean())}
    stat = E.groupby(["determined", "狀態"]).size()
    # ── 標籤與結果句 ──
    jj = J["主（determined＝1）"]
    labA = "測得出（＋）" if jj.get("判語", "").startswith("結果②") else ("測得出（−）" if jj.get("判語", "").startswith("結果③") else "測不出")
    labB = PF["main"]["標籤"]
    a47 = json.load(open(os.path.expanduser("~/tw-p17/backtest/resultsUSA34/A4/summary.json"), encoding="utf-8"))
    a47c = [x for x in a47["件"] if x["件"] == "A4-7" and "剔除" in x["名稱"]]
    adj = "相鄰件 A4-7（指數成分剔除，台股移植、已結案、另計 N）：" + ("、".join(f"{x['名稱']} {x['標籤']}" for x in a47c) if a47c else "見 resultsUSA34/A4") + "；⛔ 不以 C4 取代、⛔ 不退 N"
    if labA == "測得出（＋）":
        sA = f"被踢出 S&P 500／400 的股票，之後一年平均贏大盤 {jj['平均'] * 100:.1f} 點（2016～2025）；⚠ 文獻 1989～2017 是約 20 點"
    else:
        sA = f"2016 年後被踢股看不出贏大盤（之後一年平均超額 {jj['平均'] * 100:+.1f} 點、月分群 95% CI {jj['lo'] * 100:+.1f}～{jj['hi'] * 100:+.1f}）；Arnott 的效果在大型成長股時代沒有重現"
    pre = f"隨機挑也有 {FKb['p（隨機年化 ＞ ^SP500TR）']:.1%}；" if FKb["p（隨機年化 ＞ ^SP500TR）"] >= 0.05 else ""
    mm = PF["main"]
    sB = (pre + f"組合層（8 槽、升回指數才賣）年化中位 {mm['年化中位']:+.1%}／回落 {mm['回落中位']:.1%}（^SP500TR {bref['年化']:+.1%}／{bref['回落']:.1%}）⇒ {labB}；"
          f"持有天數中位 {mm['持有天數_中位（逐種子中位）']:.0f}、窗尾仍持有 {mm['窗尾仍持有件數（逐種子中位）']:.0f} 筆")
    covw = cov["252日"]["本快取可算比例（主事件）"]
    sent = sA + "。" + sB + "。" + adj + "。" + (f"⚠ 被踢後一年價格可算 {covw:.0%} ＜ 95% ⇒ 結果偏樂觀（缺價者多半後來下市）。" if covw < 0.95 else "") + f"公告日資料庫沒有 ⇒ 公告到生效那段不可量。{K.SURV}。"
    pri = [{"先驗": "甲 平均 ＞ 0（約七成）", "結果": f"{jj['平均']:+.2%}", "對": bool(jj["平均"] > 0)},
           {"先驗": "甲 測得出（約四成五）", "結果": labA, "對": labA == "測得出（＋）"},
           {"先驗": "效果量小於文獻 20 點（約八成）", "結果": f"{jj['平均'] * 100:+.1f} 點", "對": bool(jj["平均"] < 0.20)},
           {"先驗": "扣跌深對照後剩一半以下（約五成五）", "結果": f"{CT.get('跌深對照（事件 − 同十分位）', {}).get('平均', np.nan):+.2%} vs {jj['平均']:+.2%}",
            "對": bool(CT.get("跌深對照（事件 − 同十分位）", {}).get("平均", np.nan) < 0.5 * jj["平均"]) if jj["平均"] > 0 else None},
           {"先驗": "乙 合格或另列（約三成五）", "結果": labB, "對": labB in ("合格", "另列")}]
    card = {"件": "C4", "名稱": "剔除股反彈（被踢出 S&P 500／400 之後）", "登錄": f"USREG-B4 seq1 sha {K.REG['C4'][1]}（→ C4）", "裁定": K.RULING, "N": 2,
            "標籤": {"甲 事件層": labA, "乙 組合層": labB},
            "三欄（描述）": {g: f"{J[g].get('平均', np.nan):+.2%}（n {J[g].get('n')}）{J[g].get('判語', '')}" for g in ("只S&P500剔除", "只S&P400剔除")},
            "條件出場必報": {k: mm.get(k) for k in ("持有天數_平均（逐種子中位）", "持有天數_中位（逐種子中位）", "持有天數_p10", "持有天數_p90", "最長持有（200 顆最大）",
                                                 "窗尾仍持有件數（逐種子中位）", "窗尾仍持有件數（範圍）", "離頂距離中位（出場價÷持有期最高收盤−1）", "出場原因（訊號）", "下市結算筆數（逐種子中位）")},
            "相鄰件": adj, "結果句": sent,
            "偏離": ["公告日臂拿掉：資料庫只有生效日、⛔ 沒有公告日（裁定 seq321 照字面）", "主結果只用 determined＝1；含 determined＝0 的版本只描述",
                     "價格用 A3 快取（881c86a 聯集轉接層）；資料庫 removals_analysis 另用 Yahoo／Tiingo 與改名接續，本快取沒有的那些股票計「無價格」（覆蓋率兩版都報）"],
            "補讀法": [f"C4-1～C4-9（researchUSC_c4.py docstring，{READ_TS} 寫死）", f"K1～K11（researchUSC.py，{K.READ_TS}）"],
            "相對門檻（seq321 §五）": "≥ 5 美元是固定值（登錄寫明理由：避免雞蛋水餃股、⛔ 不看報酬訂）；照報"}
    out = {"卡片": card, "甲": J, "甲_其他天期": HD, "對照": CT, "假訊號": {"甲": FKa, "乙": FKb}, "乙": {k: v for k, v in PF.items()}, "基準": bref,
           "第一個進場日": str(cal[t0].date()), "每年事件數（determined＝1，含未過濾）": {str(k): v for k, v in yr.to_dict("index").items()},
           "排除（非主動剔除）": {"|".join(str(x) for x in k): int(v) for k, v in exc.items()}, "事件狀態": {"|".join(str(x) for x in k): int(v) for k, v in stat.items()},
           "覆蓋": cov, "先驗": pri, "資料": {"剔除表": K.NEW_COMMIT, "價格": P.meta["data_commit"]}, "算於": K.now_tpe(), "秒": round(time.time() - T0)}
    E.to_pickle(os.path.join(K.WORK, "c4_events.pkl"))
    K.jdump(out, "C4.json")
    K.log("[C4] 甲 %s｜乙 %s" % (labA, labB), "c4.log")
    return out

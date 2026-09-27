# -*- coding: utf-8 -*-
"""稽核 ② 2（seq3 §二 第 2 列、§七之六；裁定 seq257 順 5）：四類單獨「跌 −10% 加半份（攤平）」重測。回測線，2026-09-28。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchAudit2_2 [--procs 2]
    獨立查核：~/tw-p16/.venv/bin/python backtest/researchAudit2_2_check.py

原件：researchQuad.py（5b367571db；補三處 cd50b91eb6）。確認段 AD10 配對差 +2.053%（CI 不含 0 ⇒ 好）。
問題：K4 只對「不加碼、放現金」；K2 只抱 120 日。
═══ 照原件、⛔ 不改（import researchQuad：stock_data、first_trig、exec_day、COST、段界）═══
  母體 eligible ∩ gate3；量測日收盤判、次一交易日開盤進場 e；x ＝ e＋H−1；x 日沒成交 ⇒ x 以前最後一根有效收盤（＝ 停止交易強制出場：開）；
  進場日漲停／停牌不建；硬斷點 [e, x] 剔除；兩段只收整筆落在段內的持有（探索 e ≥ 2017-03-02 ∧ x ≤ 2021-12-30；確認 e ≥ 2022-01-03 ∧ x ≤ 2026-08-24）
  AD10：判定日 d ∈ [e, x−1] 第一個「收盤 ≤ P0×90/100」⇒ d 之後第一個可買開盤 s（s ＜ x）加 0.5 單位；diff ＝ 0.5 ×（c_x ÷ o_s − 1 − 0.585%）；CI ＝ 進場月分群 CR0；
  出口與結果 ＝ avgdown.exit_result（結果② 好／③ 差／其餘 分不出）
═══ 本件新增（⭐ 開跑前寫死；本線讀法）═══
  面板：量測日 ≤ 2026-03-02 用原件的 resultsp4/panel.csv.gz（照原件）；之後用 resultsp9_engine/panel_ext.csv.gz（量測日到 2026-08-03）
        ⇒ H60 確認段可收到 2026-05 的進場。⚠ panel_ext 舊段比 resultsp4 少 1,061 列（eligible 少 57 股-月、重疊列 eligible 全同；本檔計數）⇒ 舊段不換
  K2 持有天數 H ∈ {60, 120, 240}（240 ≈ 一年＝「更長」）；三個 H 都報兩段；規則 AD10 不重挑（原件在 H120 探索段挑出）；另報 5 種加碼規則在各 H 探索段的平均（描述）
  K4 三個對照（都在【同一批被觸發的持有】上逐筆配對，判定量 ＝ AD10 − 對照，同一 CI／出口規則）：
    ① 隨機日加碼：同一筆持有，加碼日改為 [e＋1, x−1] 內可買開盤中均勻抽一天（rng default_rng([20260928, H, crc32(sid), e])），同 0.5 單位、同成本、抱到同一 x
    ② 同日改買 0050：同一個 s，加的 0.5 單位改買 0050（0050 開盤無效 ⇒ s 起第一個 0050 開盤有效日、仍須 ＜ x；件數必報），抱到 x（0050 收盤 ffill），成本 0.385%
    ③ 基準②（前 20 日同分位）：加進去那 0.5 單位的報酬 X ＝ c_x ÷ o_s − 1；對照 ȳ ＝ 同一進場批（同 e、同 x、保留的持有）在 d 當天
       前 20 日報酬（avgdown.r20_cal：第 20 根有效 K 棒前）同十分位（avgdown.deciles，批內、依股票代號序）的其他股，各自 d 之後第一個可買開盤 s_k（＜ x）
       到 x 的報酬等權平均；判定量 ＝ 0.5 ×（X − ȳ）（同一個 0.5 單位、成本兩邊相同互抵）；d 當天 r20 不可算或同十分位沒有可買的配對股 ⇒ 不進此項、件數必報
  「穩」只在：三個 H 的確認段結果全同、且三個對照全是結果② 才寫
  組合層描述（原件 port）：不重跑（本件只問單筆層的對照與天數）
  閘：H120 兩段的每筆 d_AD10 ＝ resultsQuad explore_diffs／confirm_diffs 逐位元（同 sid、同 e）
輸出 backtest/resultsAudit2/2/
"""
from __future__ import annotations

import argparse
import json
import os
import time
import zlib
from multiprocessing import Pool

import numpy as np
import pandas as pd

from . import researchQuad as Q
from . import research11 as R11
from . import avgdown as AV

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "resultsAudit2", "2")
PANEL_EXT = os.path.join(HERE, "resultsp9_engine", "panel_ext.csv.gz")
HS = (60, 120, 240)
ADDS = ["AU10", "AU20", "AD10", "AD20", "AH40"]
COST_ETF = 0.00385
_W: dict = {}


def _init(cal, off, b60, b200, o50, c50ff):
    Q._init(cal, off, b60, b200)
    _W.update(o50=o50, c50ff=c50ff)


def work(args):
    sid, market, rows = args                       # rows：[(e, seg, H)]
    S = Q.stock_data(sid, market)
    if S is None:
        return sid, [{"sid": sid, "market": market, "e": e, "seg": seg, "H": H, "status": "無資料"} for e, seg, H in rows], None
    cal = Q._G["cal"]; ncal = len(cal); o, c, lv = S["o"], S["c"], S["lv"]
    o50, c50ff = _W["o50"], _W["c50ff"]
    out = []
    for e, seg, H in rows:
        x = e + H - 1
        r = {"sid": sid, "market": market, "e": e, "seg": seg, "H": H}
        if x >= ncal:
            r["status"] = "超出日曆"; out.append(r); continue
        if not S["ok_buy"][e]:
            r["status"] = "進場日漲停或停牌"; out.append(r); continue
        if bool(AV.brk_vec(S["cs_pb"], S["cs_g5"], e, x)[0]):
            r["status"] = "硬斷點"; out.append(r); continue
        P0 = float(o[e]); j = int(lv[x]); cj = float(c[j])
        base = float(cj / P0 - 1.0 - Q.COST)
        r.update(status="保留", base=base, x=x)
        for code in ADDS:
            d = Q.first_trig(code, S, e, x, P0)
            s = Q.exec_day(S, d, "buy", x) if d >= 0 else -1
            r[f"d_{code}"] = float(0.5 * (cj / o[s] - 1.0 - Q.COST)) if s >= 0 else 0.0
            r[f"t_{code}"] = int(s >= 0)
            if code == "AD10":
                r["trig_d"] = d if s >= 0 else -1; r["s"] = s
        if r["t_AD10"]:
            s = r["s"]
            cand = np.flatnonzero(S["ok_buy"][e + 1:x]) + e + 1
            rng = np.random.default_rng([20260928, H, zlib.crc32(sid.encode()), e])
            sr = int(cand[rng.integers(len(cand))])
            r["s_rand"] = sr; r["d_rand"] = float(0.5 * (cj / o[sr] - 1.0 - Q.COST))
            s50 = s
            while s50 < x and not (np.isfinite(o50[s50]) and o50[s50] > 0):
                s50 += 1
            if s50 < x:
                r["s50"] = s50; r["s50_delay"] = s50 - s
                r["d_0050"] = float(0.5 * (c50ff[x] / o50[s50] - 1.0 - COST_ETF))
            r["X"] = float(cj / o[s] - 1.0)
        out.append(r)
    r20 = AV.r20_cal(c, S["bars"])
    clv = np.where(lv >= 0, c[np.maximum(lv, 0)], np.nan)
    return sid, out, (o.astype(float), clv.astype(float), S["nxt_buy"].astype(np.int32), r20)


def ci(d, mon):
    s = Q.ci_stats(d, mon)
    s["判定"] = Q.verdict(s["結果"])
    return s


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--procs", type=int, default=2); ap.add_argument("--limit", type=int, default=None); a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    logf = open(os.path.join(OUT, "run.log"), "w", encoding="utf-8"); T0 = time.time()

    def log(m):
        m = f"[{time.time() - T0:6.0f}s] {m}"; print(m, flush=True); logf.write(m + "\n"); logf.flush()
    log(f"===== researchAudit2_2（四類單獨 AD10 重測）{pd.Timestamp.now(tz='Asia/Taipei'):%Y-%m-%d %H:%M}（台北）procs {a.procs} =====")
    D = Q.D
    cal = D.load_calendar(); ncal = len(cal); pos = {d: i for i, d in enumerate(cal)}
    e0, c1, c2, w1 = (int(cal.searchsorted(pd.Timestamp(s))) for s in (Q.E0, Q.C1, Q.C2, Q.W1))
    U = Q.RA.load_universe(None)
    from . import p4_features as P4F
    pe = P4F.read_panel(PANEL_EXT)
    po = P4F.read_panel(os.path.join(HERE, "resultsp4", "panel.csv.gz"))
    k_ = ["stock_id", "measure_date", "eligible"]
    old_md = po["measure_date"].max()
    pe_old = pe[pe["measure_date"] <= old_md][k_].sort_values(k_[:2]).reset_index(drop=True)
    po_ = po[k_].sort_values(k_[:2]).reset_index(drop=True)
    same_panel = bool(len(pe_old) == len(po_) and (pe_old["stock_id"].values == po_["stock_id"].values).all()
                      and (pe_old["measure_date"].values == po_["measure_date"].values).all()
                      and (pe_old["eligible"].astype(bool).values == po_["eligible"].astype(bool).values).all())
    mm = pe[pe["measure_date"] <= old_md][k_].merge(po[k_], on=k_[:2], how="outer", indicator=True, suffixes=("_e", "_o"))
    bb = mm[mm["_merge"] == "both"]
    pdiff = {"重疊列": int(len(bb)), "只在 resultsp4": int((mm["_merge"] == "right_only").sum()), "只在 panel_ext": int((mm["_merge"] == "left_only").sum()),
             "只在 resultsp4 且 eligible": int(po.merge(mm[mm["_merge"] == "right_only"][k_[:2]], on=k_[:2])["eligible"].astype(bool).sum()),
             "重疊列 eligible 不同": int((bb["eligible_e"].astype(bool) != bb["eligible_o"].astype(bool)).sum())}
    S = {"原件": "researchQuad.py 5b367571db／cd50b91eb6", "面板差（panel_ext 舊段 vs resultsp4）": pdiff,
         "閘": {"panel_ext 舊段（≤ resultsp4 最後量測日）stock×月×eligible ＝ resultsp4": same_panel,
                                                         "resultsp4 最後量測日": str(old_md.date()), "panel_ext 最後量測日": str(pe["measure_date"].max().date())}}
    log(f"[面板] {S['閘']}")
    pp = pd.concat([po, pe[pe["measure_date"] > old_md][list(po.columns)]], ignore_index=True)
    p = pp[pp["eligible"].astype(bool) & pp["stock_id"].isin(set(U["stock_id"]))].copy()
    p["e"] = p["measure_date"].map(pos).astype(int) + 1
    rows = []
    for H in HS:
        x = p["e"] + H - 1
        seg = np.where((p["e"] >= e0) & (x <= c1), "explore", np.where((p["e"] >= c2) & (x <= w1), "confirm", ""))
        q = p.assign(seg=seg, H=H); rows.append(q[q["seg"] != ""])
    P = pd.concat(rows, ignore_index=True)
    if a.limit:
        P = P[P["stock_id"].isin(sorted(P["stock_id"].unique())[:a.limit])]
    mk = U.set_index("stock_id")["market"]
    s50 = D.load_stock("0050", "twse", cal).df
    c50ff = pd.Series(s50["close"].to_numpy(float)).ffill().to_numpy(); o50 = s50["open"].to_numpy(float)
    off = Q.RA.TR.load_official()
    b60, b200 = R11.regime_below(c50ff, 60), R11.regime_below(c50ff, 200)
    tasks = [(sid, mk.get(sid, "twse"), list(zip(g["e"].astype(int), g["seg"], g["H"].astype(int)))) for sid, g in P.groupby("stock_id")]
    out, ARR = [], {}
    with Pool(a.procs, initializer=_init, initargs=(cal, off, b60, b200, o50, c50ff)) as pool:
        for sid, r, arr in pool.imap_unordered(work, tasks, chunksize=8):
            out += r
            if arr is not None:
                ARR[sid] = arr
    K = pd.DataFrame(out).sort_values(["H", "seg", "sid", "e"]).reset_index(drop=True)
    log(f"[單筆] {len(K):,} 列｜狀態 {K.groupby(['H', 'seg'])['status'].value_counts().to_dict()}")
    # ── 閘：H120 d_AD10 ＝ 原件逐位元
    g_ok = {}
    for seg, fn in (("explore", "explore_diffs.csv.gz"), ("confirm", "confirm_diffs.csv.gz")):
        ref = pd.read_csv(os.path.join(HERE, "resultsQuad", fn), dtype={"sid": str}, float_precision="round_trip")
        ref = ref[ref["status"] == "保留"] if "status" in ref else ref
        mine = K[(K["H"] == 120) & (K["seg"] == seg) & (K["status"] == "保留")]
        m = mine.merge(ref[["sid", "e", "d_AD10", "t_AD10"]], on=["sid", "e"], how="outer", suffixes=("", "_o"), indicator=True)
        g_ok[seg] = {"本件": int(len(mine)), "原件": int(len(ref)), "只在一邊": int((m["_merge"] != "both").sum()),
                     "d_AD10 不逐位元": int(sum(repr(float(u)) != repr(float(v)) for u, v in zip(m["d_AD10"], m["d_AD10_o"]) if pd.notna(u) and pd.notna(v)))}
    S["閘"]["H120 d_AD10 ＝ 原件"] = g_ok
    okg = all(v["只在一邊"] == 0 and v["d_AD10 不逐位元"] == 0 for v in g_ok.values())
    log(f"[閘] {g_ok}")
    if not okg and not a.limit:
        K.to_csv(os.path.join(OUT, "holdings.csv.gz"), index=False, float_format="%.17g")
        json.dump(S, open(os.path.join(OUT, "summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
        raise SystemExit("⛔ 閘不過")
    # ── 基準②
    sids = sorted(ARR); ix = {s: i for i, s in enumerate(sids)}
    Om = np.stack([ARR[s][0] for s in sids]); CL = np.stack([ARR[s][1] for s in sids]); NX = np.stack([ARR[s][2] for s in sids]); R20 = np.stack([ARR[s][3] for s in sids])
    del ARR
    Kr = K[K["status"] == "保留"]
    coh = {(H, e): np.array(sorted(ix[s] for s in g["sid"]), int) for (H, e), g in Kr.groupby(["H", "e"])}
    ybar = np.full(len(K), np.nan); npeer = np.zeros(len(K), int); why = {"r20不可算": 0, "沒有配對股": 0}
    dcache = {}
    tri = K.index[(K["status"] == "保留") & (K["t_AD10"] == 1)]
    for i in tri:
        H, e, d, x, sid = int(K.at[i, "H"]), int(K.at[i, "e"]), int(K.at[i, "trig_d"]), int(K.at[i, "x"]), K.at[i, "sid"]
        me = ix[sid]
        if not np.isfinite(R20[me, d]):
            why["r20不可算"] += 1; continue
        key = (H, e, d)
        if key not in dcache:
            cc = coh[(H, e)]
            dcache[key] = (cc, AV.deciles(R20[cc, d]))
        cc, dec = dcache[key]
        my = dec[np.searchsorted(cc, me)]
        pe_ = cc[(dec == my) & (cc != me)]
        if d + 1 < ncal:
            sk = NX[pe_, d + 1]
            okk = (sk >= 0) & (sk < x)
            pe_, sk = pe_[okk], sk[okk]
        else:
            pe_ = pe_[:0]; sk = pe_
        if len(pe_) == 0:
            why["沒有配對股"] += 1; continue
        f = CL[pe_, x] / Om[pe_, sk] - 1.0
        f = f[np.isfinite(f)]
        if len(f) == 0:
            why["沒有配對股"] += 1; continue
        ybar[i] = float(f.mean()); npeer[i] = len(f)
    K["ybar"] = ybar; K["n_peer"] = npeer
    K["c_rand"] = K["d_AD10"] - K["d_rand"]; K["c_0050"] = K["d_AD10"] - K["d_0050"]; K["c_b2"] = 0.5 * (K["X"] - K["ybar"])
    K.to_csv(os.path.join(OUT, "holdings.csv.gz"), index=False, float_format="%.17g")
    S["基準②沒進的件數"] = why
    log(f"[基準②] 沒進 {why}")
    # ── 彙總
    mon_of = np.array([str(t)[:7] for t in cal])
    res = {}
    for H in HS:
        for seg in ("explore", "confirm"):
            G = K[(K["H"] == H) & (K["seg"] == seg) & (K["status"] == "保留")]
            mon = mon_of[G["e"].to_numpy(int)]
            t = G["t_AD10"].to_numpy(bool)
            cell = {"n": int(len(G)), "月數": int(len(set(mon))), "觸發比例": float(t.mean()), "基準（買了就抱）平均": float(G["base"].mean()),
                    "被觸發那批抱到底平均": float(G["base"].to_numpy()[t].mean()),
                    "AD10 − 不加（原件判定量）": ci(G["d_AD10"].to_numpy(float), mon)}
            T_ = G[t]; mt = mon_of[T_["e"].to_numpy(int)]
            for k, nm in (("c_rand", "AD10 − ①隨機日加碼"), ("c_0050", "AD10 − ②同日改買 0050"), ("c_b2", "AD10 − ③基準②（前 20 日同分位）")):
                v = T_[k].to_numpy(float); okm = np.isfinite(v)
                cell[nm] = {**ci(v[okm], mt[okm]), "件數（被觸發）": int(len(v)), "進此項": int(okm.sum())}
            cell["0050 腿遞延件數"] = int((T_["s50_delay"].fillna(0) > 0).sum())
            cell["加碼 5 種平均（描述）"] = {c_: float(G[f"d_{c_}"].mean()) for c_ in ADDS}
            yr = np.array([cal[e_].year for e_ in T_["e"].astype(int)])
            cell["逐年（被觸發；AD10−①／−②／−③）"] = {int(y): [float(np.nanmean(T_[k].to_numpy(float)[yr == y])) for k in ("c_rand", "c_0050", "c_b2")] for y in sorted(set(yr))}
            res[f"H{H}_{seg}"] = cell
            log(f"[H{H} {seg}] n {cell['n']}｜AD10 {cell['AD10 − 不加（原件判定量）']['mean']:+.4%} {cell['AD10 − 不加（原件判定量）']['判定']}｜"
                + "｜".join(f"{nm} {cell[nm]['mean']:+.4%} [{cell[nm]['lo']:+.4%}, {cell[nm]['hi']:+.4%}] {cell[nm]['判定']}"
                            for nm in ("AD10 − ①隨機日加碼", "AD10 − ②同日改買 0050", "AD10 − ③基準②（前 20 日同分位）")))
    S["結果"] = res
    cf = [res[f"H{H}_confirm"] for H in HS]
    S["穩（三個 H 確認段 AD10 與三個對照都是結果②）"] = bool(all(c["AD10 − 不加（原件判定量）"]["結果"] == "結果②" and
                                                  all(c[nm]["結果"] == "結果②" for nm in ("AD10 − ①隨機日加碼", "AD10 − ②同日改買 0050", "AD10 − ③基準②（前 20 日同分位）"))
                                                  for c in cf))
    json.dump(S, open(os.path.join(OUT, "summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1,
              default=lambda o_: o_.item() if hasattr(o_, "item") else str(o_))
    log(f"[完] {time.time() - T0:.0f}s")


if __name__ == "__main__":
    main()

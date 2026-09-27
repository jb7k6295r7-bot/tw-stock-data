# -*- coding: utf-8 -*-
"""PREREG外部三件 之 X2（CGO＋低波動，TEJ）與 X3（月營收創紀錄公告，Lai et al. 2026）——pre＋本體（X1 等財報，⛔ 本支不做）。
判準＝台股策略線 外部研究三件 登錄 seq1（sha d412ffe18178b3be，2026-09-27 17:08）；裁定 seq239、seq241（天數軸）、seq242（沿用預設）、seq245（發號、三處定）。

    python -m backtest.researchExt pre   [--procs 2]   ⇒ 頻率、可判定性算術（⛔ 不讀任何進場後價格）
    python -m backtest.researchExt body  [--procs 2]   ⇒ 本體

⭐ 共同：main edc6f8002f 快照（researchH2）、gate3、還原 OHLC、tradability＋delist on、成本 0.585%、含已下市股；
   對照 0050 同窗（使用者判準 seq141：年化中位 ＞ 0050 且 年化÷|回落| ≥ 0050 比值 ⇒ 合格；只過前者 ⇒ 另列）；
   ⭐ 結果句必附「出處為公開研究、原文數字未必可重現」。主窗 2017-03-02～2026-08-24（早年段待資料庫補 shares／還原，⛔ 本輪不跑）。

═══ X2（⛔ 不計 N、全段描述；結果句必附「原文期間內、等於已看過」；seq245 §二）═══
 A1 CGO_t ＝ (C_t − RP_t)／C_t；RP_t ＝ Σ_{n=0..99} P_{t−n}·w_n ／ Σ w_n，w_n ＝ V_{t−n}·Π_{s=1..n}(1 − V_{t−n+s})（交易日曆回看 100 日）
    P ＝ 成交金額 ÷ 成交股數 × 當日還原係數（登錄「本專案補」）；V ＝ 成交股數 ÷ 發行股數（shares 只 ffill、⛔ 不 bfill，p4_features.load_shares）；
    無成交日 V＝0（權重 0）；★ V ＞ 1（當日周轉率 ＞ 100%）⇒ 截到 1 並計數（原文沒寫；描述件，不停）。C ＝ 還原收盤；t ＝ 換股日前一交易日、須有有效 K 棒。
 A2 TV100 ＝ [t−99, t] 內相鄰有效 K 棒還原收盤日報酬的樣本標準差（ddof＝1），報酬數 ≥ 75。
 A3 母體：gate3；到 t 為止有效 K 棒 ≥ 100（「上市櫃滿 100 個交易日」；快照自 2015-01 起 ⇒ 期初以快照內根數計）；TV100、CGO 可算。
 A4 選股：TV100 升冪取前 ⌈10%·N⌉（同值依代號）⇒ 其中 CGO 降冪取前 50（同值依代號）；等權。
 A5 換股：月初（該月第一個交易日）開盤進；出場 ＝ 下一個換股日前一交易日收盤（simulate_mtm 慣例；持續持有的檔每期照付一次來回 0.585%，⚠ 偏保守）。
    天數軸（seq241 ②）：5 個月（主格；原文 2005-01 起算的節奏）／月換／季換（2005-01 起每 3 個月）。
 A6 引擎 research11.simulate_mtm（n_slots＝50、cash zero、tradable＋delist；候選 ≤ 50 ⇒ 無抽籤）；窗內年化／回落 ＝ rerun17.win_metrics（245）。
 A7 描述：只含存活股（快照末仍掛牌）版；假訊號臂 ＝ 每期從低波動候選池隨機抽 50 檔（30 次，種子 20260925＋r）⇒ 看 CGO 排序有沒有作用。

═══ X3（N_前段 ＋1；判定只用原文期間以外；登錄 §四）═══
 B1 母體：gate3 ∧ 上市（原文只上市）。月營收 ＝ mops/revenue_hist（快照 2015-01 起）＋ 早年月營收（~/earlydata/3edc0e2206 main，2003-01～2014-12；
    (stock_id, period) 去重取最後一列）⇒ ⭐「之前所有可得月份」＝ 兩者合併（★ 只用快照 2015 起的件數另報）。
 B2 創紀錄 ＝ 當期營收 ＞ 該公司之前所有可得月份最高（嚴格 ＞）且之前有值的月份 ≥ 24。
 B3 公告日 T ＝ 期別次月 10 日之後第一個交易日（research34.rebalance_dates，pub_day 10；MOPS 實際申報時戳本快照沒有 ⇒ 用法定期限，逐字標）；
    進場 T+1 開盤、抱 20 日（px(T+21)／open(T+1)）；T 須有有效 K 棒。
 B4 量 X ＝ R_e −（EW_20(T+1) − 0.585%），EW ＝ researchM.ew_open 在【gate3 上市】母體（登錄「同月全母體」＝ 本件母體）；主 CI 月分群、非重疊 SE 第二欄。
 B5 狀態（PREREGM Q2 同序）：合併 20 日 → 硬斷點 [T, T+21] → T+1 停牌 → T+1 開盤漲停；T 當日無有效 K 棒 ⇒ 剔除計數。
 B6 期間：⭐ 原文期間暫取 2010～2024（登錄「往嚴」；全文取不到：SSRN／ScienceDirect／ResearchGate 皆 403，只讀到摘要）⇒
    判定格 ＝ T ∈ [2025-01-01, 窗尾−21]（早年段 2004～2009 待資料）；原文期間內（2017-03-02～2024-12-31）只描述。
 B7 描述格：加強條件 ＝ 公告前 20 日漲 ≥ 10%（還原 close_T ÷ 往前第 20 根有效 K 棒收盤 − 1 ≥ 0.10）且 T 日三大法人合計（stocks_inst total）＜ 0
    ⇒ 讀法看方向為負（seq245）；60 日（T+61）；組合版 10 檔（simulate_mtm，抽籤，種子 102000＋r，200 顆）× 抱 20／60／120 日 對 0050。
 B8 與營飆 v1 重疊（必報）：營飆 v1 ＝ resultsList/and_signals_ext.csv.gz 的 AND 訊號 ∧ 0050 在 t−1 高於 200 日均線（rerun17.regime_mask；list_prereg10 L5）；
    重疊 ＝ 同檔、進場同曆月；報重疊比例與去重疊後的 X。
 B9 假訊號臂（新預設）：判定格與全窗描述各一；同檔、只排除「存在保留真事件 T_r ∈ [t−20, t]」的日子；可抽日 ＝ 有效 K 棒、在該段；抽數 ＝ 該檔真事件數；
    ⛔ 不合併；斷點 [t, t+21] → T+1 停牌 → 開盤漲停 剔除；種子 [20260925＋r, crc32(代號)]；30 次；x／30 ＝ CI 不含 0 的次數（分 ＋／−）。
"""
from __future__ import annotations
import os, sys, time, json, glob, zlib, math
from collections import Counter
from multiprocessing import Pool
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
import researchH2 as H2                               # 快照、chdir ⇒ repo
D, TR, UG, R11 = H2.D, H2.TR, H2.UG, H2.R
import researchM_freq as RF
import researchM as TWM
from backtest import research34 as R34
from backtest import p4_features as P4F
from backtest import rerun17 as RR

OUT = "backtest/resultsExt"
W0, W1, SHA = H2.W0, H2.W1, H2.SHA
COST = H2.COST_RT
EARLY_REV = os.path.expanduser("~/earlydata/3edc0e2206/main/data/mops/revenue_hist")
ORIG_END_X3 = "2024-12-31"
ORIG_END_X2 = "2025-06-30"
CAD = {"5個月（主格）": 5, "月換": 1, "季換": 3}
N_PICK, LOWVOL = 50, 0.10
_G = {}


def _init(cal, mfirst, x3ev):
    _G.update(cal=cal, mfirst=mfirst, x3ev=x3ev)


def load_one(args):
    sid, market = args
    cal, mfirst = _G["cal"], _G["mfirst"]; n = len(cal)
    st = D.load_stock(sid, market, cal)
    if st is None:
        return None
    df = st.df
    o = df["open"].to_numpy(float); c = df["close"].to_numpy(float)
    valid = np.isfinite(c); bars = np.flatnonzero(valid)
    if len(bars) == 0:
        return None
    raw = pd.read_csv(os.path.join(D.DATA, "stocks", sid + ".csv"), usecols=["date", "close"], dtype={"date": str}).drop_duplicates("date")
    rc = pd.Series(pd.to_numeric(raw["close"], errors="coerce").to_numpy(), pd.to_datetime(raw["date"])).reindex(cal).to_numpy(float)
    with np.errstate(invalid="ignore", divide="ignore"):
        F = np.where(valid & (rc > 0), c / rc, np.nan)
    vol = df["volume"].to_numpy(float); amt = df["amount"].to_numpy(float)
    sh = P4F.load_shares(sid, cal).to_numpy(float)
    with np.errstate(invalid="ignore", divide="ignore"):
        P = np.where(valid & (vol > 0), amt / vol * F, np.nan)
        V = np.where(valid & (vol > 0), vol / sh, 0.0)
    v_gt1 = int(np.nansum(V > 1)); V = np.clip(V, 0, 1)
    V = np.where(np.isfinite(sh) | ~valid | ~(vol > 0), V, np.nan)          # 有成交但 shares 缺 ⇒ 不可算
    nb = np.cumsum(valid)
    # X2 因子：每個月初 d 的前一交易日 t
    cgo = np.full(len(mfirst), np.nan); tv = np.full(len(mfirst), np.nan); age = np.zeros(len(mfirst), int)
    for k, d in enumerate(mfirst):
        t = d - 1
        if t < 99 or not valid[t]:
            continue
        age[k] = nb[t]
        seg = slice(t - 99, t + 1)
        cv = c[seg][valid[seg]]
        if len(cv) >= 76:
            r = cv[1:] / cv[:-1] - 1.0
            tv[k] = float(np.std(r, ddof=1))
        vr = V[seg][::-1]; pr = P[seg][::-1]
        if not np.isfinite(vr).all():
            continue
        cp = np.r_[1.0, np.cumprod(1.0 - vr)[:-1]]
        w = vr * cp
        ok = np.isfinite(pr) & (w > 0)
        if ok.any() and w[ok].sum() > 0:
            rp = float((pr[ok] * w[ok]).sum() / w[ok].sum())
            cgo[k] = (c[t] - rp) / c[t]
    pb = np.zeros(n, bool)
    for b_ in D.breakpoints(df, st.event_dates):
        if b_["rule"] in ("price", "price+gap"):
            pb[b_["pos"]] = True
    tb = TR.one(sid, cal)
    ds = TR.delist_status({sid: tb}, cal, official=_G.get("off")).get(sid)
    delisted = ds is not None and ds["status"].startswith("delisted")
    g5 = RF._g5(valid, upto=ds["last"]) if delisted else RF._g5(valid)
    inst = pd.read_csv(os.path.join(D.DATA, "stocks_inst", sid + ".csv"), usecols=["date", "total"], dtype={"date": str}).drop_duplicates("date") \
        if os.path.exists(os.path.join(D.DATA, "stocks_inst", sid + ".csv")) else None
    inst_t = pd.Series(pd.to_numeric(inst["total"], errors="coerce").to_numpy(), pd.to_datetime(inst["date"])).reindex(cal).to_numpy(float) \
        if inst is not None else np.full(n, np.nan)
    return {"sid": sid, "market": market, "o": o, "c": c, "valid": valid, "trd": tb["trd"], "up_o": tb["up_o"], "dn_o": tb["dn_o"], "dn_c": tb["dn_c"],
            "cs_pb": np.cumsum(pb).astype(np.int32), "cs_g5": np.cumsum(g5).astype(np.int32), "cgo": cgo, "tv": tv, "age": age,
            "delisted": bool(delisted), "v_gt1": v_gt1, "inst": inst_t.astype(np.float32), "first_bar": int(bars[0])}


# ═════════════ X3 事件 ═════════════
def load_rev_all():
    rev, _, _ = R34.load_revenue()                           # 快照 2015-01 起
    fs = sorted(glob.glob(os.path.join(EARLY_REV, "*.csv")))
    e = pd.concat([pd.read_csv(f, dtype=str, usecols=["stock_id", "period", "當月營收"]) for f in fs])
    e["rev"] = pd.to_numeric(e["當月營收"], errors="coerce")
    e = e.drop_duplicates(["stock_id", "period"], keep="last").pivot(index="period", columns="stock_id", values="rev")
    allr = pd.concat([e[~e.index.isin(rev.index)], rev]).sort_index()
    return allr, rev


def records(rev):
    """B2：每檔每期 ⇒ 是否創紀錄（嚴格 ＞ 之前所有有值月份的最大值，且之前有值月份 ≥ 24）。回 {sid: [period…]}。"""
    out = {}
    V = rev.to_numpy(float); per = list(rev.index)
    for j, sid in enumerate(rev.columns):
        x = V[:, j]; m = -np.inf; cnt = 0; hit = []
        for k in range(len(x)):
            if not np.isfinite(x[k]):
                continue
            if cnt >= 24 and x[k] > m:
                hit.append(per[k])
            m = max(m, x[k]); cnt += 1
        out[str(sid)] = hit
    return out


def status_x3(S, Ts, w0, wE):
    out = []; t_keep = -10 ** 9
    for T in Ts:
        if not (w0 <= T <= wE):
            continue
        if not S["valid"][T]:
            out.append((T, "剔除_T當日停牌")); continue
        f_brk = H2.brk(S, T, T + 21)
        f_halt = (not bool(S["trd"][T + 1])) or (not np.isfinite(S["o"][T + 1]))
        if t_keep < T <= t_keep + 20:
            st = "合併掉"
        elif f_brk:
            st = "剔除_硬斷點"
        elif f_halt:
            st = "剔除_T+1停牌"
        elif S["up_o"][T + 1]:
            st = "剔除_T+1開盤漲停"
        else:
            st = "保留"; t_keep = T
        out.append((T, st))
    return out


def label(c, m, c50, m50):
    k1 = c > c50; k2 = c / abs(m) >= c50 / abs(m50)
    return "合格" if (k1 and k2) else ("另列" if k1 else "不合格")


def main():
    t0 = time.time()
    mode = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1] in ("pre", "body") else "pre"
    procs = int(sys.argv[sys.argv.index("--procs") + 1]) if "--procs" in sys.argv else 2
    lim = int(sys.argv[sys.argv.index("--limit") + 1]) if "--limit" in sys.argv else None
    cal = D.load_calendar(); n = len(cal)
    w0 = int(cal.searchsorted(pd.Timestamp(W0))); w1 = int(cal.searchsorted(pd.Timestamp(W1))); wE = w1 - 21
    per = cal.to_period("M"); mfirst = np.flatnonzero(np.r_[True, per[1:] != per[:-1]])
    stocks = pd.read_csv(os.path.join(H2.H2D, "meta", "stocks.csv"), dtype=str)
    U = UG.gate3(stocks)
    if lim:
        U = U.head(lim)
    off = TR.load_official(); _G["off"] = off
    # X3 事件（只用營收與日曆）
    allr, rev_snap = load_rev_all()
    rec_all = records(allr); rec_snap = records(rev_snap)
    rd = R34.rebalance_dates(list(allr.index), cal, 10)
    x3ev = {sid: sorted({rd[p][1] for p in ps if p in rd}) for sid, ps in rec_all.items()}
    x3ev_snap = {sid: sorted({rd[p][1] for p in ps if p in rd}) for sid, ps in rec_snap.items()}
    print("[資料] 快照 {}｜gate3 {:,}｜月營收 {}～{}（早年 {} 期）｜{}".format(SHA[:10], len(U), allr.index[0], allr.index[-1],
          int((allr.index < rev_snap.index[0]).sum()), mode), flush=True)
    with Pool(procs, initializer=_init, initargs=(cal, mfirst, None)) as pool:
        res = pool.map(load_one, list(zip(U["stock_id"], U["market"])), chunksize=8)
    ST = {r["sid"]: r for r in res if r is not None}
    sids = sorted(ST)
    print("[讀檔] 可用 {:,} 檔｜{:.0f}s".format(len(ST), time.time() - t0), flush=True)
    os.makedirs(OUT, exist_ok=True)
    lst = [s for s in sids if ST[s]["market"] == "twse"]
    t_judge = int(cal.searchsorted(pd.Timestamp("2025-01-01")))
    t_orig_end = int(cal.searchsorted(pd.Timestamp(ORIG_END_X3), side="right")) - 1
    # ── X3 狀態
    X3 = {}; X3s = {}
    for s in lst:
        X3[s] = status_x3(ST[s], x3ev.get(s, []), w0, wE)
        X3s[s] = status_x3(ST[s], x3ev_snap.get(s, []), w0, wE)
    acc = Counter(st for s in lst for _, st in X3[s]); acc_s = Counter(st for s in lst for _, st in X3s[s])
    kept = [(s, T) for s in lst for T, st in X3[s] if st == "保留"]
    kj = [(s, T) for s, T in kept if T >= t_judge]; ko = [(s, T) for s, T in kept if T <= t_orig_end]
    blk = lambda L: len({min((T - w0) // 20, 114) for _, T in L})
    PRE = {"性質": "PREREG外部三件 X2／X3 pre（⛔ 未讀進場後價格）", "快照": SHA, "判定窗主窗": [W0, W1], "gate3": int(len(U)), "可用": len(ST),
           "X3": {"事件帳（合併早年營收史）": dict(acc), "事件帳（只用快照 2015 起的營收史，★ 另一讀法）": dict(acc_s),
                  "保留": len(kept), "判定格（T ≥ 2025-01-01）保留": len(kj), "判定格區段": blk(kj), "判定格n_eff上限": min(len(kj), blk(kj)),
                  "判定格依構造": "出口①（< 30）" if min(len(kj), blk(kj)) < 30 else ("出口②" if min(len(kj), blk(kj)) < 100 else "出口③"),
                  "原文期間內（2017-03～2024-12）保留": len(ko), "原文期間內區段": blk(ko),
                  "原文期間": "暫取 2010～2024（全文取不到，只讀到摘要：12 年、1 秒盤中資料、20 日平均報酬 1.95%）"},
           "X2": {"shares缺而不可算的股-月初": None}}
    # X2 母體與選股（只用 t 以前的因子）
    sel = {}; pool_sz = {}
    months = [k for k, d in enumerate(mfirst) if d > 0]
    def pick_at(k, surv=False):
        rows = [(s, ST[s]["tv"][k], ST[s]["cgo"][k]) for s in sids if ST[s]["age"][k] >= 100 and np.isfinite(ST[s]["tv"][k]) and np.isfinite(ST[s]["cgo"][k])
                and (not surv or not ST[s]["delisted"])]
        if not rows:
            return [], [], 0
        rows.sort(key=lambda r: (r[1], r[0]))
        lv = rows[:math.ceil(LOWVOL * len(rows))]
        top = sorted(lv, key=lambda r: (-r[2], r[0]))[:N_PICK]
        return [r[0] for r in top], [r[0] for r in lv], len(rows)
    base_m = 2005 * 12 + 0
    for k in months:
        d = mfirst[k]; ym = cal[d].year * 12 + cal[d].month - 1
        sel[k] = pick_at(k)
    PRE["X2"] = {"每月初母體檔數（中位）": float(np.median([sel[k][2] for k in months if sel[k][2] > 0])),
                 "低波動池（中位）": float(np.median([len(sel[k][1]) for k in months if sel[k][2] > 0])),
                 "第一個可選月": str(cal[mfirst[min(k for k in months if sel[k][2] > 0)]].date()),
                 "V>1截到1的股日": int(sum(ST[s]["v_gt1"] for s in sids)),
                 "換股日數": {nm: int(sum(1 for k in months if (cal[mfirst[k]].year * 12 + cal[mfirst[k]].month - 1 - base_m) % cad == 0
                                            and w0 <= mfirst[k] <= w1)) for nm, cad in CAD.items()}}
    json.dump(PRE, open(os.path.join(OUT, "pre.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    print(json.dumps(PRE, ensure_ascii=False, indent=1, default=str), flush=True)
    if mode == "pre":
        return

    # ═════════════ 本體 ═════════════
    bench = RR.load_bench(cal)
    c50, m50, _ = RR.win_metrics(bench, 0, n, w0, w1)
    RES = {"性質": "PREREG外部三件 X2／X3 本體", "快照": SHA, "0050同窗": {"年化": c50, "回落": m50, "比值": c50 / abs(m50)}, "X2": {}, "X3": {}}
    closes = {s: pd.Series(ST[s]["c"]).ffill().to_numpy() for s in sids}
    opens = {s: ST[s]["o"] for s in sids}
    trad = {s: {"trd": ST[s]["trd"], "up_o": ST[s]["up_o"], "dn_o": ST[s]["dn_o"], "dn_c": ST[s]["dn_c"]} for s in sids}
    dl = TR.delist_status({s: trad[s] for s in sids}, cal, official=off)

    def run_port(sig, rule, N, seed, cost=COST):
        R11.COST = cost
        try:
            out = R11.simulate_mtm(sig, rule, N, np.random.default_rng(seed), closes, opens, n, return_equity=True, pick=None, d_max=None,
                                   queue_days=0, cash_mode="zero", tradable=trad, delist=dl)
        finally:
            R11.COST = COST
        return out

    def wstat(eq, a=w0, b=w1):
        c_, m_, v_ = RR.win_metrics(eq, 0, n, a, b)
        return c_, m_

    # ── X2
    def x2_sig(cad, surv=False, rng=None):
        rb = [k for k in months if (cal[mfirst[k]].year * 12 + cal[mfirst[k]].month - 1 - base_m) % cad == 0]
        rows = []
        for i, k in enumerate(rb):
            e = mfirst[k]
            if rng is None:
                names = pick_at(k, surv)[0] if surv else sel[k][0]
            else:
                pool_ = sel[k][1]
                names = list(rng.choice(pool_, size=min(N_PICK, len(pool_)), replace=False)) if pool_ else []
            x = (mfirst[rb[i + 1]] - 1) if i + 1 < len(rb) else n - 1
            for s in names:
                o_ = opens[s][e]; c_ = closes[s][x]
                if not (np.isfinite(o_) and o_ > 0 and np.isfinite(c_)):
                    continue
                rows.append({"sid": s, "entry_pos": e, "xpos_X": x, "g_X": c_ / o_ - 1.0, "month": cal[e].strftime("%Y-%m")})
        return pd.DataFrame(rows)
    x2 = {}; eq_out = {}
    for nm, cad in CAD.items():
        sg = x2_sig(cad)
        o_ = run_port(sg, "X", N_PICK, 0)
        c_, m_ = wstat(o_["equity"])
        t_x2o = int(cal.searchsorted(pd.Timestamp(ORIG_END_X2), side="right")) - 1
        co, mo = wstat(o_["equity"], w0, t_x2o); cx, mx = wstat(o_["equity"], t_x2o + 1, w1) if (w1 - t_x2o) >= 245 else (np.nan, np.nan)
        x2[nm] = {"年化": c_, "回落": m_, "比值": c_ / abs(m_), "標籤（描述）": label(c_, m_, c50, m50), "換股次數": int(sg["entry_pos"].nunique()),
                  "原文期間內（2017-03～2025-06）年化／回落": [co, mo], "交易數": o_["trades"], "槽位使用率": o_["slot_use"]}
        eq_out["X2_" + nm] = o_["equity"]
        print("[X2 {}] 年化 {:+.2%} 回落 {:+.2%}｜0050 {:+.2%}／{:+.2%}｜{}".format(nm, c_, m_, c50, m50, x2[nm]["標籤（描述）"]), flush=True)
    sg = x2_sig(5, surv=True); o_ = run_port(sg, "X", N_PICK, 0); c_, m_ = wstat(o_["equity"])
    x2["只含存活股（描述，5個月）"] = {"年化": c_, "回落": m_, "比值": c_ / abs(m_)}
    fk = []
    for r in range(int(sys.argv[sys.argv.index("--fk") + 1]) if "--fk" in sys.argv else 30):
        sg = x2_sig(5, rng=np.random.default_rng(20260925 + r)); o_ = run_port(sg, "X", N_PICK, 0); c_, m_ = wstat(o_["equity"])
        fk.append({"r": r, "年化": c_, "回落": m_, "標籤": label(c_, m_, c50, m50)})
    FK = pd.DataFrame(fk); FK.to_csv(os.path.join(OUT, "x2_fake_arm.csv"), index=False)
    x2["假訊號臂_低波動池隨機50檔（描述，5個月，30次）"] = {"年化中位": float(FK["年化"].median()), "回落中位": float(FK["回落"].median()),
                                              "年化範圍": [float(FK["年化"].min()), float(FK["年化"].max())],
                                              "主格年化的百分位": float((FK["年化"] < x2["5個月（主格）"]["年化"]).mean() * 100),
                                              "標籤分佈": FK["標籤"].value_counts().to_dict()}
    RES["X2"] = x2
    # X2 選股名單（可入庫：台股）
    pd.DataFrame([{"換股月": cal[mfirst[k]].strftime("%Y-%m"), "sid": s, "CGO": ST[s]["cgo"][k], "TV100": ST[s]["tv"][k]}
                  for k in months if sel[k][0] for s in sel[k][0]]).to_csv(os.path.join(OUT, "x2_picks_monthly.csv.gz"), index=False)
    pd.DataFrame([{"換股月": cal[mfirst[k]].strftime("%Y-%m"), "母體": sel[k][2], "低波動池": len(sel[k][1])} for k in months]).to_csv(
        os.path.join(OUT, "x2_pool_sizes.csv"), index=False)

    # ── X3 事件層
    O = np.column_stack([ST[s]["o"] for s in lst]); okO = np.column_stack([ST[s]["valid"] & np.isfinite(ST[s]["o"]) & (ST[s]["o"] > 0) for s in lst])
    PX = np.column_stack([np.where(okO[:, i], ST[s]["o"], closes[s]) for i, s in enumerate(lst)])
    EW = {H: TWM.ew_open(O, okO, PX, H) for H in (20, 60)}
    PXd = {s: PX[:, i] for i, s in enumerate(lst)}
    ANDt = pd.read_csv("backtest/resultsList/and_signals_ext.csv.gz", dtype={"sid": str})
    reg = RR.regime_mask(bench)
    yf = ANDt[[bool(reg[e - 1]) for e in ANDt["entry_pos"]]]
    yf_key = {(s, cal[int(e)].strftime("%Y-%m")) for s, e in zip(yf["sid"], yf["entry_pos"]) if int(e) < n}
    rows = []
    for s, T in kept:
        S = ST[s]; g = PXd[s][T + 21] / S["o"][T + 1] - 1.0
        c = S["c"]; vb = np.flatnonzero(S["valid"][:T + 1])
        r20 = c[T] / c[vb[-21]] - 1.0 if len(vb) > 20 else np.nan
        ok20 = len(vb) > 20 and not H2.brk(S, int(vb[-21]), T)
        g60 = (PXd[s][T + 61] / S["o"][T + 1] - 1.0) if (T + 61 <= w1 and not H2.brk(S, T, T + 61)) else np.nan
        rows.append({"sid": s, "T": T, "T_date": str(cal[T].date()), "g": g, "R": g - COST, "EW": EW[20][T + 1], "X": g - EW[20][T + 1],
                     "g60": g60, "X60": g60 - EW[60][T + 1] if np.isfinite(g60) else np.nan,
                     "r20": r20 if ok20 else np.nan, "inst_T": float(S["inst"][T]),
                     "營飆v1重疊": (s, cal[T + 1].strftime("%Y-%m")) in yf_key,
                     "期間": "判定（原文外）" if T >= t_judge else ("原文期間內" if T <= t_orig_end else "其他")})
    E = pd.DataFrame(rows)
    E["加強條件"] = (E["r20"] >= 0.10) & (E["inst_T"] < 0)
    E.to_csv(os.path.join(OUT, "x3_events.csv.gz"), index=False)

    def cell(d, col="X"):
        s_ = TWM.summ(d[col], d["T"], cal, w0)
        return s_
    J = cell(E[E["期間"] == "判定（原文外）"]); ex, rs = TWM.verdict(J)
    RES["X3"]["判定格_T≥2025-01"] = {**J, "出口": ex, "結果": rs}
    RES["X3"]["原文期間內（描述）"] = cell(E[E["期間"] == "原文期間內"])
    RES["X3"]["全窗（描述）"] = cell(E)
    RES["X3"]["加強條件（描述，讀方向為負）"] = {k: cell(E[E["加強條件"] & (E["期間"] == k)]) for k in ("判定（原文外）", "原文期間內")} | {"全窗": cell(E[E["加強條件"]])}
    RES["X3"]["60日（描述）"] = {k: TWM.summ(E.loc[(E["期間"] == k) & E["X60"].notna(), "X60"], E.loc[(E["期間"] == k) & E["X60"].notna(), "T"], cal, w0, blk=60, cap=38)
                               for k in ("判定（原文外）", "原文期間內")}
    ov = E["營飆v1重疊"]
    RES["X3"]["營飆v1重疊"] = {"重疊比例_全窗": float(ov.mean()), "重疊比例_判定格": float(E.loc[E["期間"] == "判定（原文外）", "營飆v1重疊"].mean()),
                            "營飆v1訊號數（regime t−1 開）": int(len(yf)),
                            "去重疊_判定格": cell(E[(E["期間"] == "判定（原文外）") & ~ov]), "去重疊_原文期間內": cell(E[(E["期間"] == "原文期間內") & ~ov])}
    print("[X3 判定格] n {}｜X {:+.3%}（{:+.3%} ～ {:+.3%}）｜n_eff {}｜{} {}".format(J["n"], J["平均"], J["lo"], J["hi"], J["n_eff"], ex, rs), flush=True)
    # 假訊號臂（新預設）
    def fake(seg_lo, seg_hi, sub):
        realT = {s: np.sort(g["T"].to_numpy()) for s, g in sub.groupby("sid")}
        outs = []
        for r in range(30):
            xs, Ts = [], []
            for s in sorted(realT):
                S = ST[s]; b = np.flatnonzero(S["valid"]); b = b[(b >= seg_lo) & (b <= seg_hi)]
                rt = realT[s]; k_ = np.searchsorted(rt, b, side="right"); prev = np.where(k_ > 0, rt[np.maximum(k_ - 1, 0)], -10 ** 9)
                b = b[~((k_ > 0) & (b - prev <= 20))]
                k = min(len(rt), len(b))
                rng = np.random.default_rng([20260925 + r, zlib.crc32(s.encode())])
                for T in (np.sort(rng.choice(b, size=k, replace=False)) if k else []):
                    T = int(T)
                    if H2.brk(S, T, T + 21) or (not S["trd"][T + 1]) or not np.isfinite(S["o"][T + 1]) or S["up_o"][T + 1]:
                        continue
                    xs.append(PXd[s][T + 21] / S["o"][T + 1] - 1.0 - EW[20][T + 1]); Ts.append(T)
            sf = TWM.summ(xs, Ts, cal, w0); pas = not (sf["lo"] <= 0 <= sf["hi"])
            outs.append({"r": r, "n": sf["n"], "平均X": sf["平均"], "lo": sf["lo"], "hi": sf["hi"], "判過": pas, "判過_正": pas and sf["平均"] > 0})
        F = pd.DataFrame(outs)
        return F, {"x／30": int(F["判過"].sum()), "其中(+)": int(F["判過_正"].sum()), "其中(−)": int(F["判過"].sum() - F["判過_正"].sum()),
                   "30次平均X的平均": float(F["平均X"].mean())}
    Fj, fj = fake(t_judge, wE, E[E["期間"] == "判定（原文外）"])
    Fa, fa = fake(w0, wE, E)
    pd.concat([Fj.assign(段="判定格"), Fa.assign(段="全窗")]).to_csv(os.path.join(OUT, "x3_fake_arm.csv"), index=False)
    RES["X3"]["假訊號臂（新預設）"] = {"判定格": fj, "全窗（描述）": fa}
    # 組合版（描述）
    port = {}
    for H in (20, 60, 120):
        sg = pd.DataFrame([{"sid": s, "entry_pos": int(T) + 1, "xpos_P": int(T) + H, "g_P": closes[s][int(T) + H] / ST[s]["o"][int(T) + 1] - 1.0,
                            "month": cal[int(T) + 1].strftime("%Y-%m")} for s, T in zip(E["sid"], E["T"]) if int(T) + H < n])
        cs_, ms_ = [], []
        for r in range(int(sys.argv[sys.argv.index("--pseeds") + 1]) if "--pseeds" in sys.argv else 200):
            o_ = run_port(sg, "P", 10, 102000 + r); c_, m_ = wstat(o_["equity"]); cs_.append(c_); ms_.append(m_)
        cm, mm = float(np.median(cs_)), float(np.median(ms_))
        port["抱{}日".format(H)] = {"年化中位": cm, "回落中位": mm, "比值": cm / abs(mm), "標籤（描述）": label(cm, mm, c50, m50)}
        print("[X3 組合 H{}] 年化中位 {:+.2%} 回落中位 {:+.2%} ⇒ {}".format(H, cm, mm, port["抱{}日".format(H)]["標籤（描述）"]), flush=True)
    RES["X3"]["組合版10檔（描述，全窗，200顆）"] = port
    RES["共同必附"] = "出處為公開研究、原文數字未必可重現"
    RES["X2必附"] = "原文期間內、等於已看過"
    pd.DataFrame({"date": [str(d.date()) for d in cal], **{k: v for k, v in eq_out.items()}}).to_csv(os.path.join(OUT, "x2_equity.csv.gz"), index=False)
    RES["耗時s"] = round(time.time() - t0)
    json.dump(RES, open(os.path.join(OUT, "summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    print("完成 {:.0f}s".format(time.time() - t0))


if __name__ == "__main__":
    main()

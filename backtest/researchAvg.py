# -*- coding: utf-8 -*-
"""PREREG攤平停利 本體（甲 單筆層 4 格＋乙 W1 組合層 2 格）——回測線落地。
判準＝台股策略線 登錄 seq2（sha 17449e5624991924，2026-09-25 20:43）；裁定線 seq175 §一（假訊號臂新預設）、§四（編號 PREREG攤平停利：
甲 N_前段 ＋4、乙 N_組合 ＋2；必附句）。

用法（repo 根目錄；PYTHONPATH＝~/tw-p17；Python ＝ ~/tw-p16/.venv/bin/python）：
  python backtest/researchAvg.py pre   [--procs 4] [--only A|B] [--limit N]
        ⇒ 開跑前報（⛔ 不算任何報酬）：甲 事件數、頻率、區段數、可能出口、遞延、配對組與假訊號臂的可用數；
          乙 0050 錨閘、引擎能力檢查、基準臂部位上的觸發次數與現金不足（近似）。輸出 backtest/resultsAvg/pre_A.json、pre_B.json
  python backtest/researchAvg.py body  [--procs 4] [--only A|B]
        ⇒ 本體（⛔ 等登錄核准後才跑）：甲 4 格判定＋必附句＋假訊號臂 30 次（新預設＋不排除版）＋對現金版＋H120 描述＋分組；
          乙 2 格（⛔ 目前引擎沒有對應參數 ⇒ body B 會在開頭停下，見 B0）
  --limit 只給除錯（只跑前 N 檔），⛔ 正式交件不用。

資料（登錄 甲一）：main edc6f8002f 快照（researchH2 把 D.DATA 指過去）；gate3；tradability（原始價漲跌停）＋ delist on；還原 OHLC ＝
   data.load_stock；主窗 2017-03-02～2026-08-24（2,313 交易日）；e 從 2017-03-01 起（讀法 A4）。
核心函式與讀法 A1～A11：avgdown.py（docstring）；fixture ＝ selftest_avgdown.py（pre／body 開頭先全跑，任一條不過就停）。

⭐ 本支的落地讀法（⛔ 在看任何報酬之前寫在這裡；交件逐條列出）：
 B1 判定量 X̄ ＝ 保留事件 X 的等權平均。主 CI：H20 ＝ T 所在曆月分群；H60 ＝ 以主窗起點 w0 切的 60 交易日區段（max(T − w0, 0)//60；T＝2017-03-01 那一天併入第一段，讀法 A4）；
    CR0（research11.cl_stats 同式）、1.96。n_eff ＝ min(n, 有事件的分群數)；出口 < 30 ①／30～99 ②／≥ 100 ③（PREREGH1 §五）。
    H120 ＝ 描述（X̄、中位、p10／p90），逐字寫「依構造不可判定」、⛔ 不印 CI。H60 有事件的 60 日區段 < 30 ⇒ 該格不跑（body 開頭擋）。
 B2 結果：結果② ＝ CI 不含 0 且 X̄ ＞ 0；結果③ ＝ CI 不含 0 且 X̄ ＜ 0；結果① ＝ CI 含 0（exit_signal.exit_result 同式）。
 B3 必附句 y 與 X − y：讀法 A10；X − y 的 CI ＝ 事件層 d_i ＝ X_i − ȳ_i 的同分群 CR0（只用有配對股的事件）。
 B4 假訊號臂：讀法 A11；判「同樣過關」＝ 假訊號日那一次的結果 ＝ 結果②（x／30）；結果③ 的次數也報。x ≥ 2 ⇒ 結果② 句前加 ⚠。
 B5 頻率（開跑前報）：每檔每年 ＝ 保留事件 ÷（e ≤ w1−H 的假想持有數 ÷ 12）（每檔每月一筆持有 ⇒ 12 筆 ≈ 1 股票年）；
    逐年 ＝ 該年 T 的保留事件 ÷（該年 e 的持有數 ÷ 12）；上市／上櫃依快照 stocks.csv market 欄；另報每筆持有的觸發比例。
 B6 分組（描述）：「觸發時距買進的天數」＝ T − e（交易日）三分位（該格保留事件合併 rank 後 qcut(3)）；上市／上櫃；逐年（T 的曆年）；
    事件當時 0050 在 MA60 上／下 ＝ research11.regime_below(0050 ffill 還原收盤, 60)[T]（收盤 < MA60 ⇒ 下）。
 B7 「跌型與漲型同一筆持有先後都觸發的比例」＝ 觀察期完整落在窗內（e＋119 ≤ w1）的持有中，兩型都有第一次觸發者 ÷ 全部（分先後）。

═══ 乙（W1 組合層；PREREGP9 seq9 引擎原樣）═══
 B0 ⛔⛔ 引擎 research11.simulate_mtm【沒有】登錄要的兩個參數組合（fixture F10 逐條證明；⛔ 本線不改引擎）：
    乙一 2-B ⓓ「收盤 ≤ 進場價 × 0.90 ⇒ 次日開盤加 0.5 slot」：add_rule 只有 kind ∈ {gain（≥ +x）, flag, hold}；
         gain 取負 x 方向相反（≥ −10% 幾乎天天成立）；flag 是【以股票代號】給的旗標，而觸發條件取決於【該部位】的進場價，
         S1 訊號同一檔的持有期大量重疊（相鄰重疊 1,008 列、422／918 檔）⇒ 哪一列被持有取決於種子 ⇒ 靜態旗標不可能逐位元等價。
    乙二 2-C ⓘ「收盤 ≥ 進場價 × 1.15 ⇒ 次日開盤賣一半」：trim_rule 只有「≤ −x」一個方向（x 必須在 (0,1)）；regime_trim 是看 0050。
    ⇒ pre 只做得到：0050 錨閘、基準臂部位上的觸發次數（近似）；body B 在引擎補上參數（裁定線決定、引擎維護者實作並過回歸閘）之前
      一律停在 B0。ENGINE_KW_B 兩格目前是 None；補上後只要填這兩格，其餘（閘、200 顆、判準、對照、配對差、必報）都已寫好。
 B8 乙 pre 的「觸發次數」：PREREGP9 基準臂（加減碼全關、種子 99000＋r、200 顆）每顆種子實際持有的部位上，用引擎的時序與式子
    （t 開盤讀 closes[t−1]、c/ep − 1 ≤ −0.10／≥ +0.15、t ∈ [進場＋1, 出場−1]、每部位一次、開盤無效 ⇒ 等下一天）數觸發；
    「現金不足（近似）」＝ 觸發成交日開盤的現金（前一日 equity − hold_val ＋ 當天排程出場拿回的錢）依部位進場先後扣 0.5×equity[t−1]÷8，
    不夠 ⇒ 記一次。⚠ 近似：忽略先前加碼吃掉的現金與它對之後進場的影響 ⇒ 現金不足【低估】、實際加成（成交 − 現金不足）【高估】。
    「結構上近乎不可得」看的是【實際加成次數】中位 ≤ 2（researchP9run 讀12 同；登錄 乙 必報那一句的讀法）。
    對帳：−10% 觸發 vs P9 2-C ⓐ（Ca）的 x_trim_n、+15% 觸發 vs 2-B ⓐ（Ba）的 x_add_trig（resultsP9run/seeds_arms.csv；只讀這兩欄與 eq_sha）。
 B9 乙 body（引擎補上後）：臂 ＝ 基準、乙一 By、乙二 Ci，各 200 顆；判定 ＝ 年化中位、回落中位、比值 ＝ 年化中位 ÷ |回落中位|，
    條件一 年化中位 ＞ 0050（嚴格）、條件二 比值 ≥ 0050 未捨入比值 ⇒ 合格／另列／不合格（researchP9run.label 同式）；
    對照（⛔ 不計 N）：By ⇒ m̄ 逐種子配對（p9_controls.mbar_of(o, "add") ⇒ mbar_kwargs）；Ci ⇒ ē 逐種子配對（p9_controls.ebar_control，
    成本 engine 口徑）；同現金比例 × 0050（researchP9run.measure 的 x50_*）；對基準臂的逐種子配對年化差、回落差；
    回落分型 log 口徑（主，裁定 seq174 §二）＋ simple 並列；乙一 現金不足中位 ≤ 2 ⇒ 標「結構上近乎不可得」。
"""
from __future__ import annotations
import os, sys, time, json, zlib, hashlib
from collections import Counter, defaultdict
from multiprocessing import Pool
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest")); sys.path.insert(0, os.path.expanduser("~/tw-p17"))
import researchH2 as H2                               # ⭐ D.DATA ⇒ 快照、chdir ⇒ repo
D, TR, UG = H2.D, H2.TR, H2.UG
import researchM_freq as RF                           # 只 import _g5
from backtest import avgdown as AV
from backtest import research11 as R11

OUT = "backtest/resultsAvg"
W0, W1, WIN_DAYS, SHA = H2.W0, H2.W1, H2.WIN_DAYS, H2.SHA
E_LO = "2017-03-01"
SEED_FAKE, REPS = 20260928, 30
H_JUDGE = (20, 60)
H_ALL = (20, 60, 120)
NCL = 140
_G = {}


# ═════════════ 讀檔 ═════════════
def _init(cal, w0, w1, wlo, off, mode, o50, c50ff, below60):
    _G.update(cal=cal, w0=w0, w1=w1, wlo=wlo, off=off, mode=mode, o50=o50, c50ff=c50ff, below60=below60,
              ok50=np.isfinite(o50) & (np.nan_to_num(o50) > 0))      # 讀法 A12：0050 開盤有效才算兩條腿都成交得了
    ym = np.asarray(cal.year * 12 + cal.month)
    _G["mon"] = ym - ym[wlo]
    _G["E"] = AV.month_first_days(cal, E_LO, w1)


def prep(sid, market, cal, off):
    """researchExit.prep 同式（多帶 up_o）。"""
    st = D.load_stock(sid, market, cal)
    if st is None:
        return None
    df = st.df; n = len(cal)
    o = df["open"].to_numpy(float); c = df["close"].to_numpy(float)
    valid = np.isfinite(c); bars = np.flatnonzero(valid)
    if len(bars) < 2:
        return None
    pb = np.zeros(n, bool)
    for b_ in D.breakpoints(df, st.event_dates):
        if b_["rule"] in ("price", "price+gap"):
            pb[b_["pos"]] = True
    tb = TR.one(sid, cal)
    ds = TR.delist_status({sid: tb}, cal, official=off).get(sid)
    delisted = bool(ds is not None and ds["status"].startswith("delisted"))
    g5 = RF._g5(valid, upto=ds["last"]) if delisted else RF._g5(valid)
    return {"sid": sid, "market": market, "o": o, "c": c, "valid": valid, "bars": bars,
            "trd": tb["trd"], "up_o": tb["up_o"], "dn_o": tb["dn_o"],
            "cs_pb": np.cumsum(pb).astype(np.int32), "cs_g5": np.cumsum(g5).astype(np.int32),
            "lv": AV.last_valid(valid), "delisted": delisted, "last": ds["last"] if ds else None,
            "dstatus": ds["status"] if ds else None}


def cl_key(T, H, w0, mon):
    """分群鍵：H20（與 H120 描述）＝ 曆月序號；H60 ＝ max(T − w0, 0)//60（讀法 A4：T＝2017-03-01 併入第一段）。"""
    T = np.asarray(T, int)
    return mon[T] if H != 60 else np.maximum(T - w0, 0) // 60


def work(args):
    sid, market = args
    cal, w0, w1, wlo, off, mode, mon = _G["cal"], _G["w0"], _G["w1"], _G["wlo"], _G["off"], _G["mode"], _G["mon"]
    o50, c50ff, below60 = _G["o50"], _G["c50ff"], _G["below60"]
    P = prep(sid, market, cal, off)
    if P is None:
        return None
    ncal = len(cal); body = mode == "body"
    o, c, valid = P["o"], P["c"], P["valid"]
    e_el, P0 = AV.holdings(_G["E"], P["trd"], P["up_o"], o)
    ok50 = _G["ok50"]
    nxt = {"buy": AV.next_true(AV.trade_ok(P["trd"], P["up_o"], o) & ok50), "sell": AV.next_true(AV.trade_ok(P["trd"], P["dn_o"], o) & ok50)}
    lim = {"buy": P["up_o"], "sell": P["dn_o"]}
    res = {"sid": sid, "market": market, "dstatus": P["dstatus"], "n_hold": int(len(e_el)),
           "hold_e": e_el.astype(np.int32)}
    # ── 觸發（讀法 A2、A3、A6）
    trig = {}; ded = {}; diag = {}
    for kind in AV.TYPES:
        Tl = AV.first_triggers(c, valid, e_el, P0, kind, ncal)
        Te = AV.first_triggers(c, valid, e_el, P0, kind, ncal, form="eng")
        Es, Ts, ndup = AV.dedup(e_el, Tl)
        trig[kind] = Tl; ded[kind] = (Es, Ts)
        diag[kind] = {"原始觸發": int((Tl >= 0).sum()), "去重去掉": ndup, "去重後": int(len(Ts)),
                      "字面式與引擎式不一致的持有": int((Tl != Te).sum()),
                      "T＝e": int(((Tl >= 0) & (Tl == e_el)).sum()),
                      "e＝2017-03-01的持有": int((e_el == wlo).sum()), "e＝2017-03-01且觸發": int(((e_el == wlo) & (Tl >= 0)).sum())}
    res["diag"] = diag
    comp = e_el + AV.OBS - 1 <= w1                                     # B7
    dn = trig["跌"] >= 0; up = trig["漲"] >= 0
    res["both"] = {"完整觀察期持有": int(comp.sum()), "兩型都觸發": int((comp & dn & up).sum()),
                   "先跌後漲": int((comp & dn & up & (trig["跌"] < trig["漲"])).sum()),
                   "先漲後跌": int((comp & dn & up & (trig["漲"] < trig["跌"])).sum()),
                   "只跌": int((comp & dn & ~up).sum()), "只漲": int((comp & up & ~dn).sum())}
    # ── 真事件逐格
    rows = []; cnt = {}; kept_T = {}
    for kind in AV.TYPES:
        side = AV.SIDE[kind]
        Es, Ts = ded[kind]
        for H in H_ALL:
            st, s, x, j = AV.outcome(Ts, Es, H, nxt[side], P["lv"], P["cs_pb"], P["cs_g5"], ncal, w1)
            cnt[(kind, H)] = Counter(AV.ST_NAME[int(q)] for q in st)
            k = np.flatnonzero(st == AV.ST_KEEP)
            kept_T[(kind, H)] = Ts[k]
            if len(k) == 0:
                continue
            Tk, Ek, sk, xk, jk = Ts[k], Es[k], s[k], x[k], j[k]
            if body:
                R = AV.ret(o, c, sk, jk); R0 = AV.ret0050(o50, c50ff, sk, H)
                X = AV.x_value(kind, R, R0); XC = AV.x_cash(kind, R)
            for i in range(len(k)):
                T, e, s_, x_, j_ = int(Tk[i]), int(Ek[i]), int(sk[i]), int(xk[i]), int(jk[i])
                t1 = T + 1
                why = "" if s_ == t1 else ("停牌" if not P["trd"][t1] else (("開盤漲停" if side == "buy" else "開盤跌停") if lim[side][t1] else
                                                  ("開盤缺值" if not (np.isfinite(o[t1]) and o[t1] > 0) else "0050停牌")))
                endst = "ok" if j_ == x_ else ("下市了結" if (P["delisted"] and j_ == P["last"]) else "停牌跨終點")
                row = {"sid": sid, "market": market, "kind": kind, "H": H, "e": e, "T": T, "s": s_, "x": x_, "j_end": j_,
                       "遞延天數": s_ - t1, "遞延原因": why, "終點": endst, "終點越過窗尾": bool(x_ > w1),
                       "T_e": T - e, "below60": bool(below60[T]), "cl": int(cl_key(T, H, w0, mon))}
                if body:
                    row.update(R=float(R[i]), R0=float(R0[i]), X=float(X[i]), Xcash=float(XC[i]))
                rows.append(row)
    res["cnt"] = cnt; res["rows"] = rows
    # ── 配對組與假訊號臂用的逐日陣列（窗 [wlo, w1]）
    Tw = np.arange(wlo, w1 + 1)
    em = AV.earliest_active(e_el, Tw)
    act = (em >= 0) & valid[Tw]
    r20 = AV.r20_cal(c, P["bars"])[Tw]
    res["r20u"] = np.where(act & np.isfinite(r20), r20, np.nan).astype(np.float64)
    for kind in AV.TYPES:
        tr = np.zeros(len(Tw), bool)
        t_ = trig[kind]; t_ = t_[(t_ >= wlo) & (t_ <= w1)]
        tr[t_ - wlo] = True
        res["trig_" + kind] = tr
    okc = {}; Xc = {}
    for kind in AV.TYPES:
        side = AV.SIDE[kind]
        for H in H_JUDGE:
            m = act & (Tw <= w1 - H)
            ok = np.zeros(len(Tw), bool); xv = np.full(len(Tw), np.nan)
            ii = np.flatnonzero(m)
            if len(ii):
                st, s, x, j = AV.outcome(Tw[ii], em[ii], H, nxt[side], P["lv"], P["cs_pb"], P["cs_g5"], ncal, w1)
                g = st == AV.ST_KEEP
                ok[ii[g]] = True
                if body:
                    R = AV.ret(o, c, s[g], j[g]); R0 = AV.ret0050(o50, c50ff, s[g], H)
                    xv[ii[g]] = AV.x_value(kind, R, R0)
            okc[(kind, H)] = ok; Xc[(kind, H)] = xv
            res["okc_{}_{}".format(kind, H)] = ok
            if body:
                res["Xc_{}_{}".format(kind, H)] = xv
    # ── 假訊號臂（B4；讀法 A11）的可抽日帳（pre 也報，不含報酬）
    pool_cnt = {}
    for kind in AV.TYPES:
        for H in H_JUDGE:
            Tk = kept_T[(kind, H)]
            base = Tw[act & (Tw <= w1 - H)]
            cex = AV.fake_candidates(base, Tk)
            pool_cnt[(kind, H)] = (int(len(Tk)), int(len(base)), int(len(cex)), int(max(0, len(Tk) - len(cex))))
    res["fake_pool"] = pool_cnt
    if not body:
        return res
    acc = np.zeros((REPS, 2, 2, 2, NCL, 2)); fc = np.zeros((REPS, 2, 2, 2, 3), np.int64)   # 抽出、剔除、可抽日不足
    seed2 = zlib.crc32(sid.encode("utf-8"))
    for r in range(REPS):
        rngs = (np.random.default_rng([SEED_FAKE + r, seed2]), np.random.default_rng([SEED_FAKE + r, seed2, 1]))
        for ki, kind in enumerate(AV.TYPES):
            for hi, H in enumerate(H_JUDGE):
                Tk = kept_T[(kind, H)]
                if len(Tk) == 0:
                    continue
                base = Tw[act & (Tw <= w1 - H)]
                for vi, cand in enumerate((AV.fake_candidates(base, Tk), base)):
                    m = min(len(Tk), len(cand)); fc[r, ki, hi, vi, 2] += len(Tk) - m
                    if m == 0:
                        continue
                    dr = np.sort(rngs[vi].choice(cand, size=m, replace=False))
                    ix = dr - wlo
                    ok = okc[(kind, H)][ix]
                    fc[r, ki, hi, vi, 0] += m; fc[r, ki, hi, vi, 1] += int((~ok).sum())
                    cl = cl_key(dr[ok], H, w0, mon)
                    np.add.at(acc[r, ki, hi, vi, :, 0], cl, 1.0)
                    np.add.at(acc[r, ki, hi, vi, :, 1], cl, Xc[(kind, H)][ix[ok]])
    res["fake"] = acc; res["fake_cnt"] = fc
    return res


def load_universe(lim):
    stocks = pd.read_csv(os.path.join(H2.H2D, "meta", "stocks.csv"), dtype=str)
    U = UG.gate3(stocks)
    return U.head(lim) if lim else U


def run_pool(U, cal, w0, w1, wlo, off, mode, procs, o50, c50ff, below60):
    out = []; FA = None; FC = None
    with Pool(procs, initializer=_init, initargs=(cal, w0, w1, wlo, off, mode, o50, c50ff, below60)) as pool:
        for r in pool.imap_unordered(work, list(zip(U["stock_id"], U["market"])), chunksize=4):
            if r is None:
                continue
            if "fake" in r:
                a = r.pop("fake"); c_ = r.pop("fake_cnt")
                FA = a if FA is None else FA + a; FC = c_ if FC is None else FC + c_
            out.append(r)
    out.sort(key=lambda r: r["sid"])
    return out, FA, FC


# ═════════════ 甲：配對組（讀法 A10）═════════════
def match_controls(res, K, wlo, body):
    """回每個保留事件（H20、H60）的十分位、配對股數、ȳ（body）。K 需有 sid、kind、H、T。"""
    sids = [r["sid"] for r in res]; si = {s: i for i, s in enumerate(sids)}
    RU = np.vstack([r["r20u"] for r in res])                        # (N, W)
    W = RU.shape[1]
    Dm = np.full(RU.shape, -1, np.int8)
    for k in range(W):
        Dm[:, k] = AV.deciles(RU[:, k])
    out = {}
    for kind in AV.TYPES:
        TRG = np.vstack([r["trig_" + kind] for r in res])
        for H in H_JUDGE:
            OK = np.vstack([r["okc_{}_{}".format(kind, H)] for r in res])
            XC = np.vstack([r["Xc_{}_{}".format(kind, H)] for r in res]) if body else None
            el = OK & ~TRG & (Dm >= 0)
            sel = K[(K["kind"] == kind) & (K["H"] == H)]
            dec = np.full(len(sel), -1, int); nct = np.zeros(len(sel), int); yb = np.full(len(sel), np.nan)
            ii = np.array([si[s] for s in sel["sid"]], int); kk = sel["T"].to_numpy(int) - wlo
            byday = defaultdict(list)
            for q, k in enumerate(kk):
                byday[int(k)].append(q)
            for k, qs in byday.items():
                e_ = el[:, k]; d_ = Dm[e_, k].astype(int)
                cn = np.bincount(d_, minlength=10)
                sm = np.bincount(d_, weights=XC[e_, k], minlength=10) if body else None
                for q in qs:
                    d0 = int(Dm[ii[q], k]); dec[q] = d0
                    if d0 < 0:
                        continue
                    nct[q] = int(cn[d0])
                    if body and cn[d0] > 0:
                        yb[q] = sm[d0] / cn[d0]
            out[(kind, H)] = (sel.index.to_numpy(), dec, nct, yb)
    return out


# ═════════════ 甲：開跑前報 ═════════════
def pre_report_A(res, cal, w0, w1, wlo, U):
    R = {"快照": SHA, "判定窗": [W0, W1], "e起點": E_LO, "gate3母體": int(len(U)), "可讀檔數": len(res),
         "時戳": pd.Timestamp.now(tz="Asia/Taipei").strftime("%Y-%m-%d %H:%M:%S"), "⛔": "本報不含任何報酬、價差、R_H 或 X"}
    rows = pd.DataFrame([row for r in res for row in r["rows"]])
    K = rows.copy()
    mk = {r["sid"]: r["market"] for r in res}
    # 持有數（分母）
    hold_e = {r["sid"]: r["hold_e"] for r in res}
    R["假想持有"] = {"總筆數": int(sum(len(v) for v in hold_e.values())), "每月一檔一筆（e 月數）": int(len(AV.month_first_days(cal, E_LO, w1)))}
    # 診斷
    dg = {kind: Counter() for kind in AV.TYPES}
    for r in res:
        for kind in AV.TYPES:
            dg[kind].update(r["diag"][kind])
    R["觸發診斷（讀法 A2、A3、A4、A6）"] = {AV.CELL[k] + "（" + k + "型）": dict(v) for k, v in dg.items()}
    bo = Counter()
    for r in res:
        bo.update(r["both"])
    b = dict(bo); n0 = b["完整觀察期持有"]
    R["B7_跌型與漲型同一筆持有先後都觸發"] = {**b, "兩型都觸發比例": b["兩型都觸發"] / n0, "先跌後漲比例": b["先跌後漲"] / n0,
                                        "先漲後跌比例": b["先漲後跌"] / n0, "只跌比例": b["只跌"] / n0, "只漲比例": b["只漲"] / n0}
    freq = {}; blocks = {}; defer = {}; acctd = {}; grp = {}
    cal_y = pd.DatetimeIndex(cal).year
    for kind in AV.TYPES:
        for H in H_ALL:
            key = "{}_H{}".format(AV.CELL[kind], H)
            c_ = Counter()
            for r in res:
                c_.update(r["cnt"][(kind, H)])
            acctd[key] = {"去重後事件": int(sum(c_.values())), **{k: int(v) for k, v in c_.items()}}
            k = K[(K["kind"] == kind) & (K["H"] == H)]
            T = k["T"].to_numpy(int); nn = len(T)
            # 頻率（B5）
            nh = {s: int((v <= w1 - H).sum()) for s, v in hold_e.items()}
            sy = pd.Series(nh) / 12.0
            ev = k.groupby("sid").size().reindex(sy.index, fill_value=0)
            f = {"保留事件": nn, "股票年（持有數÷12）": float(sy.sum()), "每檔每年_合併": float(ev.sum() / sy.sum()),
                 "每筆持有觸發比例": float(ev.sum() / (sy.sum() * 12))}
            big = sy >= 1
            rate = ev[big] / sy[big]
            f.update({"每檔每年_平均（持有≥12筆的股票）": float(rate.mean()), "中位": float(rate.median()), "p90": float(rate.quantile(0.9))})
            m_ = pd.Series(mk)
            for mkt, nm in (("twse", "上市"), ("tpex", "上櫃")):
                sel = (m_.reindex(sy.index) == mkt)
                f[nm] = float(ev[sel].sum() / sy[sel].sum()) if sy[sel].sum() else None
            yrs = {}
            ty = pd.Series(cal_y[T]).value_counts() if nn else pd.Series(dtype=int)
            ey = Counter()
            for s, v in hold_e.items():
                v = v[v <= w1 - H]
                ey.update(cal_y[v])
            for y in sorted(ey):
                den = ey[y] / 12.0
                num = int(ty.get(y, 0))
                yrs[str(y)] = {"事件": num, "股票年": round(den, 1), "每檔每年": num / den if den else None}
            f["逐年"] = yrs
            if H == 20:
                mon = pd.Series([str(cal[t])[:7] for t in T]).value_counts()
                allm = sorted({str(d)[:7] for d in cal[wlo:w1 - H + 1]})
                mv = mon.reindex(allm, fill_value=0)
                f["每月事件數"] = {"月數": len(allm), "0事件月": int((mv == 0).sum()), "最少": int(mv.min()), "p10": float(mv.quantile(.1)),
                               "中位": float(mv.median()), "p90": float(mv.quantile(.9)), "最多": int(mv.max()), "最多的月": str(mv.idxmax())}
            freq[key] = f
            # 區段數與可能出口
            months = len(np.unique([str(cal[t])[:7] for t in T])); b20 = len(np.unique(np.maximum(T - w0, 0) // 20))
            b60 = len(np.unique(np.maximum(T - w0, 0) // 60)); b120 = len(np.unique(np.maximum(T - w0, 0) // 120))
            if H == 20:
                nb_, unit, cap = months, "曆月", len({str(d)[:7] for d in cal[wlo:w1 - H + 1]})
            elif H == 60:
                nb_, unit, cap = b60, "60日區段", len(np.unique(np.maximum(np.arange(wlo, w1 - H + 1) - w0, 0) // 60))
            else:
                nb_, unit, cap = b120, "120日區段", len(np.unique(np.maximum(np.arange(wlo, w1 - H + 1) - w0, 0) // 120))
            ne = min(nn, nb_)
            if H == 120:
                ex = "依構造不可判定（描述）"
            else:
                ex = ("①②③ 都可能 ⇒ 判定" if ne >= 100 else ("只可能 ① 或 ②（到不了 ③）⇒ 判定；落 ② 句首加「樣本中等」" if ne >= 30
                                                            else "只可能出口① ⇒ 依構造不可判定、⛔ 不跑"))
            blocks[key] = {"保留事件": nn, "分群單位": unit, "有事件的區段數": int(nb_), "理論上限": int(cap), "n_eff": int(ne),
                           "20日區段數（另一讀法）": int(b20), "可能出口": ex, "身分": "判定格" if H in H_JUDGE else "描述"}
            dd = k["遞延天數"].to_numpy(int) if nn else np.zeros(0, int)
            defer[key] = {"保留事件": nn, "有遞延": int((dd > 0).sum()),
                          "遞延原因": {kk: int(v) for kk, v in Counter(k.loc[k["遞延天數"] > 0, "遞延原因"]).items()} if nn else {},
                          "遞延天數分佈": {str(kk): int(v) for kk, v in sorted(Counter(dd[dd > 0]).items())},
                          "終點狀態": {kk: int(v) for kk, v in Counter(k["終點"]).items()} if nn else {},
                          "終點越過窗尾（讀法 A5）": int(k["終點越過窗尾"].sum()) if nn else 0,
                          "T<主窗起點（讀法 A4）": int((T < w0).sum()), "T＝e（讀法 A3）": int((k["T_e"] == 0).sum()) if nn else 0}
            if nn:
                te = k["T_e"]
                q = pd.qcut(te.rank(method="first"), 3, labels=["快", "中", "慢"])
                grp[key] = {"T−e 分位（交易日）": [float(x) for x in te.quantile([0, 1 / 3, 2 / 3, 1]).to_numpy()],
                            "T−e 三分位各組件數": {str(a): int(v) for a, v in Counter(q).items()},
                            "T−e 三分位各組範圍": {g: [int(te[q == g].min()), int(te[q == g].max())] for g in ("快", "中", "慢")},
                            "0050在MA60下": int(k["below60"].sum()), "0050在MA60上": int((~k["below60"]).sum()),
                            "上市": int((k["market"] == "twse").sum()), "上櫃": int((k["market"] == "tpex").sum()),
                            "逐年件數": {str(y): int(v) for y, v in sorted(Counter(cal_y[T]).items())}}
    R["事件帳（去重後、逐格狀態）"] = acctd
    R["甲六第一列_頻率（B5）"] = freq
    R["甲三_區段數與可能出口"] = blocks
    R["遞延（開盤漲停／跌停／停牌）"] = defer
    R["分組件數（B6；不含報酬）"] = grp
    # 配對組可用數
    mc = match_controls(res, K[K["H"].isin(H_JUDGE)], wlo, body=False)
    mcr = {}
    for (kind, H), (idx, dec, nct, _) in mc.items():
        mcr["{}_H{}".format(AV.CELL[kind], H)] = {"事件": int(len(idx)), "r20可算（有十分位）": int((dec >= 0).sum()),
                                                  "有配對股": int((nct > 0).sum()), "沒有配對股": int((nct == 0).sum()),
                                                  "配對股數_中位": float(np.median(nct[nct > 0])) if (nct > 0).any() else 0.0,
                                                  "配對股數_最少": int(nct[nct > 0].min()) if (nct > 0).any() else 0,
                                                  "十分位分佈": {str(a): int(v) for a, v in sorted(Counter(dec).items())}}
    R["甲五_配對組可用數（讀法 A10；不含報酬）"] = mcr
    fp = {}
    for kind in AV.TYPES:
        for H in H_JUDGE:
            a = np.array([r["fake_pool"][(kind, H)] for r in res])
            fp["{}_H{}".format(AV.CELL[kind], H)] = {"真事件": int(a[:, 0].sum()), "候選日_不排除": int(a[:, 1].sum()),
                                                     "候選日_排除過去20日": int(a[:, 2].sum()), "每次可抽日不足（排除版）": int(a[:, 3].sum())}
    R["甲五_假訊號臂可抽日（讀法 A11）"] = fp
    R["下市狀態（delist_status）"] = dict(Counter(r["dstatus"] for r in res))
    R["H60_實際區段<30而停"] = [k_ for k_, v in blocks.items() if k_.endswith("_H60") and v["有事件的區段數"] < 30]
    R["ETF"] = "0050 本身、00631L、00757、00910 ⛔ 不在母體（gate3 只含股票）⇒ 照寫「無法判定」"
    return R, K


# ═════════════ 甲：本體統計 ═════════════
def cell_stats(x, T, H, cal, w0):
    x = np.asarray(x, float); T = np.asarray(T, int); n = len(x)
    if n == 0:
        return {"n": 0}
    out = {"n": int(n), "X̄": float(x.mean()), "中位": float(np.median(x)), "X＞0比例": float((x > 0).mean()),
           "最差": float(x.min()), "p10": float(np.percentile(x, 10)), "p90": float(np.percentile(x, 90))}
    if H == 120:
        out.update(區段數_120日=int(len(np.unique(np.maximum(T - w0, 0) // 120))), 註="依構造不可判定（120 日區段不到 20 段；⛔ 不印 CI）")
        return out
    g = np.array([str(cal[t])[:7] for t in T]) if H == 20 else np.maximum(T - w0, 0) // 60
    m, se, ng = AV.cr0(x, g)
    cs = R11.cl_stats(x, g)
    assert abs(cs["mean"] - m) < 1e-12 and abs(cs["se"] - se) < 1e-12
    n_eff = int(min(n, ng))
    ex, rs = AV.exit_result(m, m - 1.96 * se, m + 1.96 * se, n, n_eff)
    out.update(se=se, lo=m - 1.96 * se, hi=m + 1.96 * se, 群數=int(ng), 分群單位=("曆月" if H == 20 else "60日區段"),
               n_eff=n_eff, n_eff_另一讀法_20日區段=int(min(n, len(np.unique(np.maximum(T - w0, 0) // 20)))) if H == 20 else None, 出口=ex, 結果=rs)
    return out


def desc_stats(x, T, H, cal, w0):
    x = np.asarray(x, float); T = np.asarray(T, int); ok = np.isfinite(x); x, T = x[ok], T[ok]
    if len(x) == 0:
        return {"n": 0}
    o = {"n": int(len(x)), "X̄": float(x.mean()), "中位": float(np.median(x))}
    if H == 120 or len(x) < 2:
        return o
    g = np.array([str(cal[t])[:7] for t in T]) if H == 20 else np.maximum(T - w0, 0) // 60
    m, se, ng = AV.cr0(x, g)
    o.update(lo=m - 1.96 * se, hi=m + 1.96 * se, 群數=int(ng))
    return o


MUST = "這是全市場的平均，不是對這一檔的預測。"


def sentence(kind, H, J, y, dci0, x2):
    """登錄 甲四 逐字形狀；J ＝ cell_stats；y ＝ 配對組平均；dci0 ＝ X − y 的 CI 含 0；x2 ＝ 假訊號結果② 次數。"""
    pct = lambda v: "{:+.2f}%".format(v * 100)
    pre = "〔H{}〕".format(H)
    if J["出口"] == "出口②":
        pre += "樣本中等（n_eff＝{}）：".format(J["n_eff"])
    if J["出口"] == "出口①":
        body = "樣本不足以分辨"
    elif kind == "跌":
        body = {"結果②": "買進後跌 10% 再加碼，加的那一份平均比同一筆錢買 0050 好 {}（95% CI 下緣 {}）".format(pct(J["X̄"]), pct(J["lo"])),
                "結果③": "跌 10% 後加碼，平均比拿去買 0050 差 {} ⇒ 本件不支持攤平".format(pct(-J["X̄"])),
                "結果①": "分不出來（{}，95% CI {} ～ {}）⇒ 本件不支持因為跌了而加碼".format(pct(J["X̄"]), pct(J["lo"]), pct(J["hi"]))}[J["結果"]]
    else:
        body = {"結果②": "漲 15% 後賣一半換 0050，平均比續抱好 {}（95% CI 下緣 {}）".format(pct(J["X̄"]), pct(J["lo"])),
                "結果③": "漲 15% 後續抱，平均比賣一半換 0050 好 {} ⇒ 本件不支持先停利".format(pct(-J["X̄"])),
                "結果①": "分不出來（{}，95% CI {} ～ {}）⇒ 本件不支持因為漲了而先賣".format(pct(J["X̄"]), pct(J["lo"]), pct(J["hi"]))}[J["結果"]]
    warn = "⚠ 隨機挑日子也有 {}／30 次同樣過關。".format(x2) if (J.get("結果") == "結果②" and x2 >= 2) else ""
    tail = "同期沒觸發的持股換 0050：{}".format(pct(y)) + ("；這與{} 本身無關。".format("跌 10%" if kind == "跌" else "漲 15%") if dci0 else "。")
    return "{}{}{}。{}{}".format(warn, pre, body, MUST, tail)


# ═════════════ 設定 ═════════════
def setup(argv):
    procs = int(argv[argv.index("--procs") + 1]) if "--procs" in argv else 4
    lim = int(argv[argv.index("--limit") + 1]) if "--limit" in argv else None
    cal = D.load_calendar()
    w0 = int(cal.searchsorted(pd.Timestamp(W0))); w1 = int(cal.searchsorted(pd.Timestamp(W1)))
    assert str(cal[w0].date()) == W0 and str(cal[w1].date()) == W1 and w1 - w0 + 1 == WIN_DAYS
    E = AV.month_first_days(cal, E_LO, w1)
    wlo = int(E[0])
    assert str(cal[wlo].date()) == E_LO, cal[wlo]
    U = load_universe(lim); off = TR.load_official()
    s50 = D.load_stock("0050", "twse", cal).df
    o50 = s50["open"].to_numpy(float); c50ff = pd.Series(s50["close"].to_numpy(float)).ffill().to_numpy()
    below60 = R11.regime_below(c50ff, 60)
    bad50 = [str(cal[i].date()) for i in range(wlo, len(cal)) if not (np.isfinite(o50[i]) and o50[i] > 0)]
    assert bad50 == ["2025-06-11", "2025-06-12", "2025-06-13", "2025-06-16", "2025-06-17"], bad50   # 讀法 A12：已知的 0050 停牌 5 日
    return procs, lim, cal, w0, w1, wlo, U, off, o50, c50ff, below60


def main_pre_A(argv):
    import selftest_avgdown as STA
    t0 = time.time(); fx = STA.run_all()
    procs, lim, cal, w0, w1, wlo, U, off, o50, c50ff, below60 = setup(argv)
    print("[資料] 快照 {}｜判定窗 [{}, {}]｜e 起 {}｜gate3 {:,} 檔｜pre（⛔ 不算報酬）".format(SHA[:10], W0, W1, E_LO, len(U)), flush=True)
    res, _, _ = run_pool(U, cal, w0, w1, wlo, off, "pre", procs, o50, c50ff, below60)
    print("[讀檔＋偵測] {:,} 檔｜{:.0f}s".format(len(res), time.time() - t0), flush=True)
    R, _ = pre_report_A(res, cal, w0, w1, wlo, U)
    R["fixture"] = fx
    os.makedirs(OUT, exist_ok=True)
    json.dump(R, open(os.path.join(OUT, "pre_A.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    print("完成 甲 pre {:.0f}s ⇒ {}/pre_A.json".format(time.time() - t0, OUT), flush=True)


def main_body_A(argv):
    import selftest_avgdown as STA
    t0 = time.time()
    print("[時點] 甲 本體開跑 {}".format(time.strftime("%F %T")), flush=True)
    fx = STA.run_all()
    procs, lim, cal, w0, w1, wlo, U, off, o50, c50ff, below60 = setup(argv)
    pre = json.load(open(os.path.join(OUT, "pre_A.json"), encoding="utf-8"))
    assert not pre["H60_實際區段<30而停"], "⛔ 開跑前報 H60 < 30 段 ⇒ 該格不跑（改寫停在這裡，⛔ 不自己改規則）"
    res, FA, FC = run_pool(U, cal, w0, w1, wlo, off, "body", procs, o50, c50ff, below60)
    print("[讀檔＋偵測＋假訊號] {:,} 檔｜{:.0f}s".format(len(res), time.time() - t0), flush=True)
    R_pre, _ = pre_report_A(res, cal, w0, w1, wlo, U)
    keys = ("甲三_區段數與可能出口", "事件帳（去重後、逐格狀態）", "甲五_配對組可用數（讀法 A10；不含報酬）", "甲五_假訊號臂可抽日（讀法 A11）")
    same = all(json.loads(json.dumps(R_pre[k], ensure_ascii=False, default=str)) == pre[k] for k in keys)
    print("[查核0] 本體重數的事件帳、區段數、配對可用數、假訊號可抽日 ＝ 開跑前報：{}".format(same), flush=True)
    assert same, "⛔ 本體事件帳與開跑前報不同"
    K = pd.DataFrame([row for r in res for row in r["rows"]])
    mc = match_controls(res, K[K["H"].isin(H_JUDGE)], wlo, body=True)
    K["decile"] = -1; K["n_ctrl"] = 0; K["y_bar"] = np.nan
    for (kind, H), (idx, dec, nct, yb) in mc.items():
        K.loc[idx, "decile"] = dec; K.loc[idx, "n_ctrl"] = nct; K.loc[idx, "y_bar"] = yb
    K["d"] = K["X"] - K["y_bar"]
    K["T_date"] = [str(cal[t].date()) for t in K["T"]]; K["e_date"] = [str(cal[t].date()) for t in K["e"]]
    K["s_date"] = [str(cal[t].date()) for t in K["s"]]; K["end_date"] = [str(cal[int(t)].date()) for t in K["j_end"]]
    K["year"] = [cal[t].year for t in K["T"]]
    t_first = time.strftime("%F %T")
    print("[時點] 本體第一次彙總報酬 {}｜{:.0f}s".format(t_first, time.time() - t0), flush=True)
    RES = {"快照": SHA, "判定窗": [W0, W1], "e起點": E_LO, "gate3母體": int(len(U)), "可讀檔數": len(res),
           "時點": {"本體第一次彙總報酬": t_first}, "fixture": fx}
    J = {}; FK = {}
    for ki, kind in enumerate(AV.TYPES):
        for hi, H in enumerate(H_JUDGE):
            key = "{}_H{}".format(AV.CELL[kind], H)
            k = K[(K["kind"] == kind) & (K["H"] == H)]
            s_ = cell_stats(k["X"], k["T"], H, cal, w0)
            km = k[np.isfinite(k["y_bar"])]
            ydesc = {"有配對的事件": int(len(km)), "沒有配對的事件": int(len(k) - len(km)), "y": float(km["y_bar"].mean()),
                     "X̄（有配對的事件）": float(km["X"].mean())}
            dstat = desc_stats(km["d"], km["T"], H, cal, w0)
            dci0 = bool(dstat["lo"] <= 0 <= dstat["hi"])
            fk = {}
            for vi, vn in enumerate(("新預設_只排除過去20日", "不排除（描述）")):
                fr = [AV.fake_eval(FA[r, ki, hi, vi]) for r in range(REPS)]
                fr = [f for f in fr if f]
                fk[vn] = {"x2／30（結果②＝同樣過關）": sum(1 for f in fr if f["結果"] == "結果②"),
                          "x3／30（結果③）": sum(1 for f in fr if f["結果"] == "結果③"), "次數": len(fr),
                          "假訊號日平均X": float(np.mean([f["E"] for f in fr])), "假X範圍": [float(min(f["E"] for f in fr)), float(max(f["E"] for f in fr))],
                          "結果分佈": dict(Counter(f["結果"] for f in fr)), "平均n": float(np.mean([f["n"] for f in fr])),
                          "帳（30次合計：抽出、剔除、可抽日不足）": [int(v) for v in FC[:, ki, hi, vi].sum(axis=0)], "逐次": fr}
            FK[key] = fk
            x2 = fk["新預設_只排除過去20日"]["x2／30（結果②＝同樣過關）"]
            dd = k["遞延天數"].to_numpy(int)
            J[key] = {**s_, "必附句_配對組": {**ydesc, "X−y": dstat, "X−y的CI含0": dci0},
                      "假訊號": {vn: {kk: v for kk, v in fk[vn].items() if kk != "逐次"} for vn in fk},
                      "對現金版（描述）": desc_stats(k["Xcash"], k["T"], H, cal, w0),
                      "遞延": {"有遞延": int((dd > 0).sum()), "遞延原因": dict(Counter(k.loc[k["遞延天數"] > 0, "遞延原因"]))},
                      "終點狀態": dict(Counter(k["終點"]))}
            J[key]["給使用者的句子"] = sentence(kind, H, s_, ydesc["y"], dci0, x2)
            print("[{}] n {:,}｜n_eff {}｜X̄ {:+.3f}%（CI {:+.3f} ～ {:+.3f}）｜{} {}｜y {:+.3f}%｜X−y CI含0 {}｜假訊號 結果② {}／30".format(
                key, s_["n"], s_["n_eff"], s_["X̄"] * 100, s_["lo"] * 100, s_["hi"] * 100, s_["出口"], s_["結果"], ydesc["y"] * 100, dci0, x2), flush=True)
    RES["判定4格"] = J
    RES["同型兩H"] = {AV.CELL[kind]: {"H20": J[AV.CELL[kind] + "_H20"]["結果"], "H60": J[AV.CELL[kind] + "_H60"]["結果"],
                                    "結論相同": J[AV.CELL[kind] + "_H20"]["結果"] == J[AV.CELL[kind] + "_H60"]["結果"]} for kind in AV.TYPES}
    must = {}
    h120 = {}
    for kind in AV.TYPES:
        k = K[(K["kind"] == kind) & (K["H"] == 120)]
        h120[AV.CELL[kind]] = {**cell_stats(k["X"], k["T"], 120, cal, w0), "對現金版": cell_stats(k["Xcash"], k["T"], 120, cal, w0)}
    must["H120_描述（依構造不可判定）"] = h120
    grp = {}
    for kind in AV.TYPES:
        for H in H_JUDGE:
            k = K[(K["kind"] == kind) & (K["H"] == H)].copy()
            k["三分位"] = pd.qcut(k["T_e"].rank(method="first"), 3, labels=["快", "中", "慢"])
            ds = lambda d: desc_stats(d["X"], d["T"], H, cal, w0)
            grp["{}_H{}".format(AV.CELL[kind], H)] = {
                "觸發時距買進天數三分位": {q: {**ds(k[k["三分位"] == q]), "T−e範圍": [int(k.loc[k["三分位"] == q, "T_e"].min()), int(k.loc[k["三分位"] == q, "T_e"].max())]}
                                   for q in ("快", "中", "慢")},
                "上市上櫃": {nm: ds(k[k["market"] == m_]) for m_, nm in (("twse", "上市"), ("tpex", "上櫃"))},
                "逐年": {str(y): ds(k[k["year"] == y]) for y in sorted(k["year"].unique())},
                "0050_MA60": {"上": ds(k[~k["below60"]]), "下": ds(k[k["below60"]])}}
    must["分組（描述）"] = grp
    RES["必報"] = must
    RES["ETF"] = "0050 本身、00631L、00757、00910 ⛔ 不在母體（gate3 只含股票）⇒ 無法判定"
    RES["N帳"] = {"N_前段": "+4（甲 4 格）", "不計": "H120 描述、對現金版、配對組、假訊號臂（兩版）、分組"}
    os.makedirs(OUT, exist_ok=True)
    cols = ["sid", "market", "kind", "H", "e", "e_date", "T", "T_date", "s", "s_date", "x", "j_end", "end_date", "遞延天數", "遞延原因",
            "終點", "終點越過窗尾", "T_e", "below60", "cl", "year", "R", "R0", "X", "Xcash", "decile", "n_ctrl", "y_bar", "d"]
    K[cols].to_csv(os.path.join(OUT, "A_events_kept.csv.gz"), index=False)
    json.dump({k: v for k, v in FK.items()}, open(os.path.join(OUT, "A_fake_reps.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    np.savez_compressed(os.path.join(OUT, "A_fake_acc.npz"), acc=FA, cnt=FC)
    RES["時點"]["本體完成"] = time.strftime("%F %T")
    json.dump(RES, open(os.path.join(OUT, "A_summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    print("完成 甲 body {:.0f}s".format(time.time() - t0))


# ═════════════ 乙（W1 組合層）═════════════
# 引擎：add_rule kind="loss"／trim_rule kind="gain"（d609e89a95）、trim_proceeds="next"（12c39cb810）、nx_cap（b1717d5c19）
# 登錄 seq4（sha ea31ef7567f1d5e4）乙二 ①：一般新部位仍 8 槽（N_MAIN）；賣得現金買下一檔可用到第 9、10 槽 ⇒ nx_cap＝10
ENGINE_KW_B = {"By": {"add_rule": {"kind": "loss", "x": 0.10, "size": 0.5, "short": "skip"}},
               "Ci": {"trim_rule": {"kind": "gain", "x": 0.15, "frac": 0.5}, "trim_proceeds": "next", "nx_cap": 10},
               # ⛔ 描述臂（不判、不計 N）：乙三 (丙) 8 槽原樣版（待買只能用 8 槽）／乙三 賣得現金閒置版
               "Ci8": {"trim_rule": {"kind": "gain", "x": 0.15, "frac": 0.5}, "trim_proceeds": "next"},
               "Ci0": {"trim_rule": {"kind": "gain", "x": 0.15, "frac": 0.5}}}
B_CELLS = [("base", "基準臂（加減碼全關）", False), ("By", "乙一 2-B ⓓ 個股收盤 ≤ 進場 −10% ⇒ 加 0.5 slot", True),
           ("Ci", "乙二 2-C ⓘ 個股收盤 ≥ 進場 +15% ⇒ 賣一半、賣得現金買下一檔（待買可到第 9、10 槽）", True),
           ("Ci8", "乙三描述 (丙)：同乙二但待買只能用 8 槽（seq3 原樣）", False),
           ("Ci0", "乙三描述：賣半、賣得現金閒置", False)]
_BG = {}


def _b_engine_kw(key):
    if key == "base":
        return {}
    kw = ENGINE_KW_B.get(key)
    if kw is None:
        raise SystemExit("⛔ B0：引擎 research11.simulate_mtm 沒有「{}」要的參數組合（見 fixture F10）⇒ 停；"
                         "要跑須先由裁定線決定、引擎維護者擴充並過回歸閘，再填 ENGINE_KW_B".format(key))
    return kw


def _b_positions(au):
    """基準臂 audit ⇒ 部位（sid, 進場 t, ep）與每天排程出場拿回的淨現金。"""
    buys = []; net = defaultdict(float)
    for a in au:
        if a["side"] == "buy" and "kind" not in a:
            buys.append((int(a["t"]), a["sid"], float(a["px"])))
        elif a["side"] == "sell" and "kind" not in a:
            net[int(a["t"])] += float(a["amt"]) - float(a["cost"])
    return buys, net


def _b_seed_pre(r):
    """B8：一顆種子的基準臂 ⇒ 觸發次數（−10%／+15%）與現金不足（近似）；⛔ 不取年化／回落，只驗 eq_sha。"""
    from backtest import researchP9run as P
    G = P._G; closes, opens = G["closes"], G["opens"]
    au = []
    o = P.sim({}, P.SEED0 + r, audit=au)
    eq, hv = o["equity"], o["hold_val"]
    buys, net = _b_positions(au)
    xpos = _BG["xpos"]
    out = {"r": r, "eq_sha": P.sha(eq), "部位": len(buys)}
    adds = []
    for kind, f in (("dn", lambda z: z <= -0.10), ("up", lambda z: z >= 0.15)):
        ntr = nex = nbl = 0
        for t0, sid, ep in buys:
            x = xpos[(sid, t0)]
            if x - 1 < t0 + 1:
                continue
            c1 = closes[sid][t0:x - 1].astype(float)             # 對應 t ＝ t0＋1 … x−1 讀的 closes[t−1]
            z = c1 / ep - 1.0
            hit = np.flatnonzero(np.isfinite(z) & f(z))
            if not len(hit):
                continue
            ntr += 1
            tt = t0 + 1 + int(hit[0])
            op = opens[sid][tt:x].astype(float)
            ok = np.flatnonzero(np.isfinite(op) & (op > 0))
            if not len(ok):
                nbl += 1; continue
            nex += 1
            if kind == "dn":
                adds.append((tt + int(ok[0]), t0, sid))
        out[kind + "_觸發"] = ntr; out[kind + "_成交"] = nex; out[kind + "_到出場都成交不了"] = nbl
    short = 0; day = None; cash = 0.0
    for t, t0, sid in sorted(adds):
        if t != day:
            day = t; cash = float(eq[t - 1] - hv[t - 1]) + net.get(t, 0.0)
        want = 0.5 * float(eq[t - 1]) / P.N_MAIN
        if cash < want:
            short += 1
        else:
            cash -= want
    out["dn_現金不足_近似"] = short
    return out


def main_pre_B(argv):
    import selftest_avgdown as STA
    from backtest import researchP9run as P
    from backtest import rerun17 as RR
    t0 = time.time()
    procs = int(argv[argv.index("--procs") + 1]) if "--procs" in argv else 4
    fx = STA.run_all(only=("F10",))
    S = {"時戳": pd.Timestamp.now(tz="Asia/Taipei").strftime("%Y-%m-%d %H:%M:%S"), "⛔": "本報不含乙兩格的年化、回落或任何比值",
         "B0_引擎能力": fx.get("F10")}
    logs = []
    S["設定"] = P.setup(lambda x: logs.append(x))
    G = P._G; cal, w0, w1, bench = G["cal"], G["w0"], G["w1"], G["bench"]
    bw = RR.bench_row(cal, bench, w0, w1 + 1)
    ok1 = repr(bw["cagr"]) == repr(P.ANCHOR[0]) and repr(bw["mdd"]) == repr(P.ANCHOR[1])
    S["閘一_0050錨"] = {"年化": repr(bw["cagr"]), "回落": repr(bw["mdd"]), "逐位元": ok1, "比值（未捨入）": bw["cagr"] / abs(bw["mdd"])}
    print("[閘一] 0050 主窗 年化 {!r}／回落 {!r} ⇒ 逐位元 {}".format(bw["cagr"], bw["mdd"], ok1), flush=True)
    if not ok1:
        raise SystemExit("⛔ 閘一不過")
    sig = G["sig"]
    _BG["xpos"] = {(s, int(e)): int(x) for s, e, x in zip(sig["sid"], sig["entry_pos"], sig["xpos_H120"])}
    ov = 0; pairs = 0; sids = set()
    for sid, g in sig.sort_values("entry_pos").groupby("sid"):
        e = g["entry_pos"].to_numpy(); x = g["xpos_H120"].to_numpy()
        ov += int((e[1:] <= x[:-1]).sum())
        for i in range(len(e)):
            for j in range(i + 1, len(e)):
                if e[j] <= x[i]:
                    pairs += 1; sids.add(sid)
    S["B0_S1同檔持有期重疊"] = {"訊號列": int(len(sig)), "檔": int(sig["sid"].nunique()), "相鄰重疊列": ov, "重疊對": pairs, "有重疊的檔": len(sids),
                           "意義": "以股票代號給的靜態旗標無法表達「依該部位進場價」的條件 ⇒ add_rule kind＝flag 不能逐位元代替 2-B ⓓ"}
    with Pool(procs) as pool:
        rows = pool.map(_b_seed_pre, range(P.REPS), chunksize=10)
    B = pd.DataFrame(rows).set_index("r").sort_index()
    ref = pd.read_csv(os.path.join(P.HERE, "resultsP9run", "seeds_arms.csv"), usecols=["arm", "r", "eq_sha", "x_trim_n", "x_add_trig", "x_add_short", "x_add_n"])
    base = ref[ref["arm"] == "base"].set_index("r").sort_index()
    ca = ref[ref["arm"] == "Ca"].set_index("r").sort_index(); ba = ref[ref["arm"] == "Ba"].set_index("r").sort_index()
    det = bool((B["eq_sha"] == base.loc[B.index, "eq_sha"]).all())
    S["閘_基準臂重現（eq_sha 逐顆＝resultsP9run）"] = det
    print("[閘] 基準臂 200 顆 eq_sha ＝ resultsP9run：{}".format(det), flush=True)
    q = lambda s: {"中位": float(s.median()), "p10": float(s.quantile(.1)), "p90": float(s.quantile(.9)), "最少": int(s.min()), "最多": int(s.max())}
    S["B8_基準臂部位上的觸發（乙 pre；近似見讀法 B8）"] = {
        "每顆種子部位數": q(B["部位"]),
        "乙一_−10%觸發": q(B["dn_觸發"]), "乙一_−10%成交": q(B["dn_成交"]), "乙一_現金不足_近似（低估）": q(B["dn_現金不足_近似"]),
        "乙一_實際加成_近似（成交−現金不足；高估）": q(B["dn_成交"] - B["dn_現金不足_近似"]),
        "乙一_加成中位≤2（結構上近乎不可得）？": bool((B["dn_成交"] - B["dn_現金不足_近似"]).median() <= 2),
        "乙二_+15%觸發": q(B["up_觸發"]), "乙二_+15%成交": q(B["up_成交"]),
        "對帳_−10%成交 vs P9 Ca x_trim_n": {"逐顆相同": int((B["dn_成交"] == ca.loc[B.index, "x_trim_n"]).sum()), "Ca中位": float(ca["x_trim_n"].median()),
                                             "差_中位": float((B["dn_成交"] - ca.loc[B.index, "x_trim_n"]).median())},
        "對帳_+15%觸發 vs P9 Ba x_add_trig": {"逐顆相同": int((B["up_觸發"] == ba.loc[B.index, "x_add_trig"]).sum()), "Ba中位": float(ba["x_add_trig"].median()),
                                              "差_中位": float((B["up_觸發"] - ba.loc[B.index, "x_add_trig"]).median()),
                                              "參考_Ba 現金不足中位（2-B ⓐ 實跑）": float(ba["x_add_short"].median()), "參考_Ba 加成中位": float(ba["x_add_n"].median())}}
    os.makedirs(OUT, exist_ok=True)
    B.to_csv(os.path.join(OUT, "pre_B_seeds.csv"))
    json.dump(S, open(os.path.join(OUT, "pre_B.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    print(json.dumps(S["B8_基準臂部位上的觸發（乙 pre；近似見讀法 B8）"], ensure_ascii=False, indent=1))
    print("完成 乙 pre {:.0f}s".format(time.time() - t0))


def _b_arm(args):
    from backtest import researchP9run as P
    from backtest import researchp9 as P9
    from backtest import p9_controls as C
    key, r = args
    au = [] if key == "base" else None
    o = P.sim(_b_engine_kw(key), P.SEED0 + r, audit=au)
    waits = o.pop("x_nx_waits", None)                  # 串列 ⇒ P.measure 的 float() 吃不下；另彙總（必報：等待天數分佈）
    row = {"arm": key, "r": r, "seed": P.SEED0 + r, **P.measure(o)}
    if waits is not None:
        w_ = np.asarray(waits, float)
        row.update({"nxw_n": int(len(w_)), "nxw_med": float(np.median(w_)) if len(w_) else np.nan,
                    "nxw_p90": float(np.quantile(w_, .9)) if len(w_) else np.nan, "nxw_mean": float(w_.mean()) if len(w_) else np.nan,
                    "nxw_max": float(w_.max()) if len(w_) else np.nan, "nxw_le20": int((w_ <= 20).sum())})
    for kind in ("單日暴跌型", "延續下跌型", "混合型"):
        row["ddlog_" + kind] = 0
    for e_ in P9.dd_events(o["equity"], P._G["w0"], P._G["w1"] + 1):
        k, _, _ = P9.dd_type(o["equity"], e_["peak"], e_["trough"], scale="log")
        row["ddlog_" + k] += 1
    if key == "By":
        row["mbar"] = C.mbar_of(o, "add")
    return row


def _b_ctrl(args):
    from backtest import researchP9run as P
    from backtest import rerun17 as RR
    from backtest import p9_controls as C
    kind, r, param = args
    G = P._G
    if kind == "mbar":
        o = P.sim(C.mbar_kwargs(param, G["ncal"]), P.SEED0 + r)
        V = o["equity"]; expo = C.ebar_of(o["equity"], o["hold_val"], G["w0"], G["w1"])
    else:
        au = []
        o = P.sim({}, P.SEED0 + r, audit=au)
        rs = C.ebar_control(o["equity"], o["hold_val"], au, G["cal"], G["w0"], G["w1"], param, cost_mode="engine")
        V = rs["V"]; expo = rs["ebar_realized"]
    c, m, v = RR.win_metrics(V, o["first"], o["end"], G["w0"], G["w1"])
    return {"kind": kind, "r": r, "param": float(param), "cagr": float(c), "mdd": float(m), "vol": float(v), "expo": float(expo)}


def main_body_B(argv):
    """乙 2 格＋乙三描述 2 臂（登錄 seq4）。引擎參數見 ENGINE_KW_B（2026-09-26 由 None 填上；閘、200 顆、判準、對照、必報照原寫法）。"""
    from backtest import researchP9run as P
    from backtest import rerun17 as RR
    t0 = time.time()
    procs = int(argv[argv.index("--procs") + 1]) if "--procs" in argv else 4
    for k in ("By", "Ci"):
        _b_engine_kw(k)                                            # ⛔ 沒有參數 ⇒ 這裡就停
    logs = []
    S = {"設定": P.setup(lambda x: logs.append(x)), "閘": {}}
    G = P._G; cal, w0, w1, bench = G["cal"], G["w0"], G["w1"], G["bench"]
    bw = RR.bench_row(cal, bench, w0, w1 + 1)
    ok1 = repr(bw["cagr"]) == repr(P.ANCHOR[0]) and repr(bw["mdd"]) == repr(P.ANCHOR[1])
    S["閘"]["一_0050錨"] = ok1
    if not ok1:
        raise SystemExit("⛔ 閘一不過")
    P._G.update(c50=bw["cagr"], m50=bw["mdd"], v50=bw["vol"])
    with Pool(procs) as pool:
        rr = pd.DataFrame(pool.map(P._rr17, range(P.REPS), chunksize=10)).set_index("r").sort_index()
        ref = pd.read_csv(os.path.join(P.HERE, "resultsN17", "seeds_main.csv"), float_precision="round_trip")
        ref = ref[(ref["stage"] == "main") & (ref["cell"] == 0)].set_index("r").sort_index()
        ok3 = all(all(repr(x) == repr(y) for x, y in zip(rr[k], ref.loc[rr.index, k])) for k in ("cagr", "mdd", "vol"))
        S["閘"]["三_rerun17"] = ok3
        if not ok3:
            raise SystemExit("⛔ 閘三不過")
        A = pd.DataFrame(pool.map(_b_arm, [(k, r) for k, _, _ in B_CELLS for r in range(P.REPS)], chunksize=10))
        pb = pd.read_csv(os.path.join(P.HERE, "resultsP9run", "seeds_arms.csv"), usecols=["arm", "r", "eq_sha"])
        pb = pb[pb["arm"] == "base"].set_index("r").sort_index()
        bb = A[A["arm"] == "base"].set_index("r").sort_index()
        S["閘"]["基準臂＝resultsP9run（eq_sha 逐顆）"] = bool((bb["eq_sha"] == pb.loc[bb.index, "eq_sha"]).all())
        if not S["閘"]["基準臂＝resultsP9run（eq_sha 逐顆）"]:
            raise SystemExit("⛔ 基準臂與 P9 不同")
        by = A[A["arm"] == "By"].set_index("r").sort_index(); ci = A[A["arm"] == "Ci"].set_index("r").sort_index()
        jobs = [("mbar", r, float(by.loc[r, "mbar"])) for r in range(P.REPS)] + [("ebar", r, float(ci.loc[r, "expo"])) for r in range(P.REPS)]
        CT = pd.DataFrame(pool.map(_b_ctrl, jobs, chunksize=10))
    os.makedirs(OUT, exist_ok=True)
    A.to_csv(os.path.join(OUT, "B_seeds_arms.csv"), index=False); CT.to_csv(os.path.join(OUT, "B_seeds_controls.csv"), index=False)
    base = A[A["arm"] == "base"].set_index("r").sort_index()
    rows = []
    for k, nm, judged in B_CELLS:
        g = A[A["arm"] == k].set_index("r").sort_index()
        c, m = float(g["cagr"].median()), float(g["mdd"].median())
        lab, ratio, extra = P.label(c, m)
        row = {"arm": k, "格": nm, "判定": judged, "cagr": c, "mdd": m, "ratio": ratio, "label": lab if judged else "", "deep_note": extra,
               "d_cagr_med": float((g["cagr"] - base["cagr"]).median()), "d_mdd_med": float((g["mdd"] - base["mdd"]).median()),
               "expo": float(g["expo"].median()), "x50_cagr": float(g["x50_cagr"].median()), "x50_mdd": float(g["x50_mdd"].median())}
        row["x50_label"] = P.label(row["x50_cagr"], row["x50_mdd"])[0]
        for q in ("dd_單日暴跌型", "dd_延續下跌型", "dd_混合型", "ddlog_單日暴跌型", "ddlog_延續下跌型", "ddlog_混合型", "dd_n"):
            row[q] = float(g[q].median())
        for q in [c_ for c_ in g.columns if c_.startswith("x_")]:
            x = g[q].astype(float)
            row[q + "_med"] = float(x.median()); row[q + "_p10"] = float(x.quantile(.1)); row[q + "_p90"] = float(x.quantile(.9))
        for q in [c_ for c_ in g.columns if c_.startswith("nxw_")]:
            x = g[q].astype(float)
            row[q + "_med"] = float(x.median()); row[q + "_p10"] = float(x.quantile(.1)); row[q + "_p90"] = float(x.quantile(.9))
        if k in ("By", "Ci"):                              # 對照只給判定格；描述臂 Ci8／Ci0 另報與 Ci 的配對差
            ctl = CT[CT["kind"] == ("mbar" if k == "By" else "ebar")].set_index("r").sort_index()
            cc, cm = float(ctl["cagr"].median()), float(ctl["mdd"].median())
            wc = c >= cc; wr = ratio >= cc / abs(cm)
            row.update({"ctrl": "m̄ 逐種子配對" if k == "By" else "ē 逐種子配對", "ctrl_cagr": cc, "ctrl_mdd": cm, "ctrl_ratio": cc / abs(cm),
                        "ctrl_class": "甲'" if (wc and wr) else ("乙'" if (wc or wr) else "丙'"),
                        "pair_d_cagr_med": float((g["cagr"] - ctl["cagr"]).median()), "pair_d_mdd_med": float((g["mdd"] - ctl["mdd"]).median())})
        if k in ("Ci8", "Ci0"):
            ci_ = A[A["arm"] == "Ci"].set_index("r").sort_index()
            row.update({"vs_Ci_d_cagr_med": float((g["cagr"] - ci_["cagr"]).median()), "vs_Ci_d_mdd_med": float((g["mdd"] - ci_["mdd"]).median())})
        if k == "By":
            row["結構上近乎不可得"] = bool(g["x_add_n"].median() <= 2) if "x_add_n" in g else None
        rows.append(row)
    TB = pd.DataFrame(rows)
    TB.to_csv(os.path.join(OUT, "B_cells.csv"), index=False)
    S["格"] = rows
    S["N帳"] = {"N_組合": "+2（乙一、乙二）", "不計": "基準臂、m̄／ē 對照、同現金比例×0050、乙三描述臂 Ci8（8 槽原樣）／Ci0（閒置）"}
    json.dump(S, open(os.path.join(OUT, "B_summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    print("完成 乙 body {:.0f}s".format(time.time() - t0))


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "pre"
    only = sys.argv[sys.argv.index("--only") + 1] if "--only" in sys.argv else "AB"
    if mode == "pre":
        if "A" in only:
            main_pre_A(sys.argv)
        if "B" in only:
            main_pre_B(sys.argv)
    elif mode == "body":
        if "A" in only:
            main_body_A(sys.argv)
        if "B" in only:
            main_body_B(sys.argv)
    else:
        raise SystemExit("用法：researchAvg.py pre|body [--procs 4] [--only A|B] [--limit N]")

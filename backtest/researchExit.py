# -*- coding: utf-8 -*-
"""PREREG出場訊號 本體（既有部位：收盤跌破 破壞價／MA20／MA60 ⇒ 隔天開盤賣 vs 續抱 H 天）——回測線落地。
判準＝台股策略線 登錄 seq3（sha 5de87a1fc7699368，2026-09-25 18:56）；裁定線 seq167 §一（編號 PREREG出場訊號，N_前段 +6）。

用法：  python backtest/researchExit.py pre    ⇒ 開跑前報（⛔ 不算任何報酬：只數事件、剔除、遞延、區段數與可能出口）
        python backtest/researchExit.py body   ⇒ 本體（6 格判定＋必報＋描述臂＋0050 描述臂③＋假訊號臂 30 次）
        選項 --procs 2（預設 2）、--limit N（只跑前 N 檔，除錯用）

資料（登錄 §一）：main edc6f8002f 快照（researchH2 把 D.DATA 指過去）；gate3；tradability（原始價漲跌停）＋ delist on
   （tradability.delist_status official）；還原 OHLC ＝ data.load_stock；主窗 2017-03-02～2026-08-24（2,313 交易日）。
訊號、賣出、終點、狀態：exit_signal.py（讀法 E1～E7 在那一支的 docstring；fixture ＝ selftest_exit_signal.py，本支開跑前先全跑）。

⭐ 本支的落地讀法（⛔ 在看任何報酬之前寫在這裡；交件逐條列出；【兩種讀法】處另一種也報件數）：
 B1 判定量 E ＝ 保留事件 R_H 的等權平均（⛔ 不扣成本）。主 CI：H20 ＝ T 所在曆月分群；H60 ＝ 以判定窗起點切的 60 交易日區段
    （區段號 ＝ (T − 窗起點)//60）分群；CR0（research11.cl_stats 同式）、1.96。
    第二欄（非重疊 SE）：H20 ＝ 20 日區段平均的標準差／√區段數（H2 R8）；H60 ＝ 60 日區段平均的標準差／√區段數。
 B2 【兩種讀法③】n_eff ＝ min(保留事件數, 有事件的獨立區段數)：⭐ H20 的「區段」＝ 主 CI 的分群單位 ＝【曆月】（登錄 §四
    「H20 ⇒ 以曆月分群；區段上限約 115」、裁定 seq165 同 PREREG限價 L7）；另一讀法 ＝ 20 日區段（PREREGM B5）⇒ 一併報數。
    H60 ＝ 60 日區段。出口：< 30 ①／30～99 ②（句首加「樣本中等」）／≥ 100 ③。
 B3 H120 ＝ 描述：E、中位、p10／p90，逐字寫「依構造不可判定」；⛔ 不印 CI（裁定 seq165 §二：區段切小會假性變窄）。
 B4 假訊號臂（登錄 §六、裁定 seq159 預設）：r ＝ 0…29，種子 [20260926＋r, crc32(sid)]（逐檔獨立 ⇒ 與行程分工無關）；
    每檔、每個判定格 (訊號, H)：該格保留真事件 n 筆 ⇒ 從該檔「有效 K 棒、至該日 ≥ 80 根、T ∈ [窗起點, 窗尾−H]、
    距該格任一保留真事件 > 20 個交易日」的日子不放回抽 n 天（不足 ⇒ 全取、另報）⇒ 照 exit_signal.statuses（合併 → 斷點 →
    賣出遞延 → 終點）與同一套 E、CI、n_eff、出口、結果 ⇒ x／30 ＝ 落結果③ 的次數；並報假訊號日平均 E 與「真 E − 假 E」。
    ⚠【兩種讀法④】「排除真事件前後 20 日」的真事件 ⭐ 取該格【保留】真事件（PREREGU B6 同）；另一讀法（原始事件）⛔ 不另跑。
 B5 對照① gate3 等權同段：EW_H(s) ＝ s 日有效 K 棒且還原開盤 > 0 的全部 gate3 股票（含日後下市者），
    ffill 還原收盤(s＋H−1)／還原開盤(s) − 1 的等權平均；超額 ＝ R_H − EW_H(s)。
    對照② 換成 0050：0050 還原收盤(s＋H−1，ffill)／還原開盤(s) − 1 − 0.1425%（多付一次買進成本）；報「換成 0050 − 續抱」。
 B6 分組 a「跌破前 60 日報酬」＝ 還原 close_T ÷ 該股往前第 60 根有效 K 棒的還原收盤 − 1；三分位 ＝ 該格全部保留事件合併 qcut(3)。
    b 事件當天狀態標籤 ＝ exit_signal.state_vec（＝ state_label.core 的 label_raw；⛔ 不套處置／注意／硬斷點閘門，那是給單檔判讀用）。
    c「門檻B 進場後 120 日內」＝ 同檔存在 build_sig_gate_b(signal="B") 的 entry_pos ≤ T ≤ entry_pos＋119（交易日曆）。
    d 上市／上櫃依快照 stocks.csv market 欄；逐年依 T 的曆年。
 B7 放棄組（研究十四）：該格 R_H ≥ 該格 p90 的事件，與其餘事件比：跌破前 60 日／20 日報酬、收盤離線多遠（close_T／線_T − 1）、
    狀態標籤分佈、上市／上櫃、MA20 斜率（MA20_T／MA20_{T−5} − 1）。⛔ 只描述。
 B8 頻率（開跑前報）：每檔每年 ＝ 保留事件 ÷ 股票年；股票年 ＝ 該檔在 [窗起點, 窗尾−H] 內從首個到最後一個有效 K 棒所跨的交易日數
    ÷ 每年交易日數（＝ 窗內交易日數 ÷ 窗的曆年數），同 researchM_freq Q6；逐年分母用該年落在跨距內的交易日數 ÷ 該年交易日數。
 B9 0050 描述臂③：同一套 exit_signal（三訊號、80 根閘、合併、[T−60, 終點] 斷點、遞延、終點）、同判定窗、H20／H60／H120；
    分群照 B1（H120 同 B3 不印 CI）；n_eff < 30 ⇒ 出口①「樣本不足以分辨」逐字照寫。
"""
from __future__ import annotations
import os, sys, time, json, zlib
from collections import Counter, defaultdict
from multiprocessing import Pool
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest")); sys.path.insert(0, os.path.expanduser("~/tw-p17"))
import researchH2 as H2                               # ⭐ D.DATA ⇒ 快照、chdir ⇒ repo
D, TR, UG, R11 = H2.D, H2.TR, H2.UG, H2.R
import researchM_freq as RF                           # 只 import _g5
from backtest import exit_signal as XS

OUT = "backtest/resultsExit"
W0, W1, WIN_DAYS, SHA = H2.W0, H2.W1, H2.WIN_DAYS, H2.SHA
SEED_FAKE, REPS = 20260926, 30
H_JUDGE = (20, 60)
H_ALL = (5, 10, 20, 60, 120)
H_VAR = (20, 60)
BUY_0050 = 0.001425
_G = {}


def _init(cal, w0, w1, off, mode):
    _G.update(cal=cal, w0=w0, w1=w1, off=off, mode=mode)
    base = cal[w0].year * 12 + cal[w0].month
    _G["mon"] = np.array([d.year * 12 + d.month - base for d in cal])


def prep(sid, market, cal, off):
    st = D.load_stock(sid, market, cal)
    if st is None:
        return None
    df = st.df; n = len(cal)
    o = df["open"].to_numpy(float); h = df["high"].to_numpy(float); l = df["low"].to_numpy(float); c = df["close"].to_numpy(float)
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
    X = {"nb": np.cumsum(valid), "nxt": XS.next_sellable(tb["trd"], tb["dn_o"], o), "lv": XS.last_valid(valid), "valid": valid,
         "trd": tb["trd"], "dn_o": tb["dn_o"], "cs_pb": np.cumsum(pb).astype(np.int32), "cs_g5": np.cumsum(g5).astype(np.int32),
         "ncal": n, "delisted": delisted, "last": ds["last"] if ds else None}
    cff = pd.Series(c).ffill().to_numpy()
    return {"sid": sid, "market": market, "o": o, "h": h, "l": l, "c": c, "cff": cff, "valid": valid, "bars": bars, "X": X,
            "dstatus": ds["status"] if ds else None}


def events_of(P):
    """回 {(rule, g): 日曆位置陣列} 與逐根線（close 規則）、近似相等診斷。"""
    bars = P["bars"]; cb, lb, hb = P["c"][bars], P["l"][bars], P["h"][bars]
    LN = XS.lines(cb, lb)
    ev = {}
    for rule in XS.RULES:
        rs = XS.raw_signals(cb, lb, rule, LN=LN)
        for g in XS.SIGS:
            ev[(rule, g)] = bars[np.flatnonzero(rs[g])]
    return ev, LN


def work(args):
    sid, market = args
    cal, w0, w1, off, mode, mon = _G["cal"], _G["w0"], _G["w1"], _G["off"], _G["mode"], _G["mon"]
    P = prep(sid, market, cal, off)
    if P is None:
        return None
    n = len(cal); bars = P["bars"]; X = P["X"]
    ev, LN = events_of(P)
    bi = np.full(n, -1); bi[bars] = np.arange(len(bars))          # 日曆位置 ⇒ 有效 K 棒索引
    # 曝露（B8）
    expo = {}
    for H in H_ALL:
        b = bars[(bars >= w0) & (bars <= w1 - H)]
        if len(b):
            yrs = Counter(cal[b[0]:b[-1] + 1].year)
            expo[H] = {"span": int(b[-1] - b[0] + 1), "by_year": dict(yrs)}
        else:
            expo[H] = {"span": 0, "by_year": {}}
    cnt = {}; rows = []
    body = mode == "body"
    if body:
        cb = P["c"][bars]; lab = XS.state_vec(P["h"][bars], P["l"][bars], cb)
        m20 = LN["乙"][0]
    kept_T = {}
    for (rule, g), Ts in ev.items():
        Hs = H_ALL if rule == "close" else H_VAR
        L, Lp = LN[g]
        for H in Hs:
            st = XS.statuses(Ts, H, X, w0, w1)
            cnt[(rule, g, H)] = Counter(r["狀態"] for r in st)
            cnt[(rule, g, H)]["連鎖讀法會合併_但主讀法保留"] = sum(1 for r in st if r["狀態"] == "保留" and r.get("連鎖讀法會合併"))
            kt = []
            for r in st:
                if r["狀態"] not in ("保留", "剔除_硬斷點", "剔除_賣不掉", "剔除_超出日曆"):
                    continue
                T = r["T"]; i = int(bi[T])
                row = {"sid": sid, "market": market, "rule": rule, "g": g, "H": H, "T": T, "狀態": r["狀態"],
                       "s": r.get("s", -1), "x": r.get("x", -1), "遞延天數": r.get("遞延天數", -1), "遞延原因": r.get("遞延原因", ""),
                       "連鎖": bool(r.get("連鎖讀法會合併", False))}
                if r["狀態"] == "保留":
                    kt.append(T)
                    row.update(j_end=r["j_end"], 終點=r["終點"])
                    cT, cP = float(P["c"][bars[i]]), float(P["c"][bars[i - 1]])
                    row.update(line=float(L[i]), line_prev=float(Lp[i]), cT=cT, cTm1=cP,
                               near_tie=bool(abs(cT - L[i]) <= 1e-9 * abs(L[i]) or abs(cP - Lp[i]) <= 1e-9 * abs(Lp[i])))
                    if body:
                        s, j = r["s"], r["j_end"]
                        row.update(P_s=float(P["o"][s]), P_end=float(P["c"][j]), R=XS.ret(P["o"], P["c"], s, j))
                        if rule == "close":
                            row.update(pre60=float(cb[i] / cb[i - 60] - 1.0), pre20=float(cb[i] / cb[i - 20] - 1.0),
                                       dist=float(cb[i] / L[i] - 1.0), ma20_slope=float(m20[i] / m20[i - 5] - 1.0) if i >= 24 else np.nan,
                                       label=lab[i])
                rows.append(row)
            if rule == "close" and H in H_JUDGE:
                kept_T[(g, H)] = np.array(sorted(kt), int)
    res = {"sid": sid, "market": market, "cnt": cnt, "rows": rows, "expo": expo, "dstatus": P["dstatus"]}
    if not body:
        return res
    res["o"] = P["o"].astype(np.float64); res["cff"] = P["cff"]
    # ── 假訊號臂（B4）
    NCL = int(mon.max() + 2)
    acc = np.zeros((REPS, 3, 2, NCL, 2)); fc = np.zeros((REPS, 3, 2, 4), np.int64)   # 抽出、合併、剔除、可抽日不足
    nb = X["nb"]; base_c = bars[nb[bars] >= XS.MIN_BARS]
    seed2 = zlib.crc32(sid.encode("utf-8"))
    for r in range(REPS):
        rng = np.random.default_rng([SEED_FAKE + r, seed2])
        for gi, g in enumerate(XS.SIGS):
            for hi, H in enumerate(H_JUDGE):
                Tk = kept_T.get((g, H), np.zeros(0, int))
                if len(Tk) == 0:
                    continue
                cand = base_c[(base_c >= w0) & (base_c <= w1 - H)]
                if len(cand):
                    k = np.searchsorted(Tk, cand)
                    dl = np.abs(cand - Tk[np.clip(k - 1, 0, len(Tk) - 1)]); dr = np.abs(Tk[np.clip(k, 0, len(Tk) - 1)] - cand)
                    cand = cand[np.minimum(dl, dr) > 20]
                m = min(len(Tk), len(cand)); fc[r, gi, hi, 3] += len(Tk) - m
                if m == 0:
                    continue
                dr_ = np.sort(rng.choice(cand, size=m, replace=False))
                st = XS.statuses(dr_, H, X, w0, w1)
                fc[r, gi, hi, 0] += m
                for q in st:
                    if q["狀態"] == "保留":
                        R = XS.ret(P["o"], P["c"], q["s"], q["j_end"])
                        cl = mon[q["T"]] if H == 20 else (q["T"] - w0) // 60
                        acc[r, gi, hi, cl, 0] += 1; acc[r, gi, hi, cl, 1] += R
                    elif q["狀態"] == "合併掉":
                        fc[r, gi, hi, 1] += 1
                    else:
                        fc[r, gi, hi, 2] += 1
    res["fake"] = acc; res["fake_cnt"] = fc
    return res


# ═════════════ 統計 ═════════════
def cell_stats(x, T, H, cal, w0):
    x = np.asarray(x, float); T = np.asarray(T, int)
    n = len(x)
    if n == 0:
        return {"n": 0}
    out = {"n": int(n), "E": float(x.mean()), "中位": float(np.median(x)), "續抱賺的比例": float((x > 0).mean()), "續抱賺的筆數": int((x > 0).sum()),
           "最差": float(x.min()), "p10": float(np.percentile(x, 10)), "p90": float(np.percentile(x, 90))}
    mon = np.array([str(cal[t])[:7] for t in T])
    blk20 = (T - w0) // 20
    if H == 120:
        out.update(區段數_120日=int(len(np.unique((T - w0) // 120))), 註="依構造不可判定（120 日區段不到 20 段；⛔ 不印 CI）")
        return out
    g = mon if H not in (60,) else (T - w0) // 60
    if H in (5, 10):
        g = mon
    m, se, ng = XS.cr0(x, g)
    cs = R11.cl_stats(x, g)
    assert abs(cs["mean"] - m) < 1e-12 and abs(cs["se"] - se) < 1e-12
    bl = blk20 if H != 60 else (T - w0) // 60
    bm = pd.Series(x).groupby(bl).mean()
    se2 = float(bm.std(ddof=1) / np.sqrt(len(bm))) if len(bm) > 1 else np.nan
    n_eff = int(min(n, ng))
    ex, rs = XS.exit_result(m, m - 1.96 * se, m + 1.96 * se, n, n_eff)
    out.update(se=se, lo=m - 1.96 * se, hi=m + 1.96 * se, 群數=int(ng), 分群單位=("曆月" if H != 60 else "60日區段"),
               se_非重疊=se2, lo_非重疊=m - 1.96 * se2, hi_非重疊=m + 1.96 * se2, 非重疊區段數=int(len(bm)),
               n_eff=n_eff, n_eff_另一讀法_20日區段=int(min(n, len(np.unique(blk20)))), 出口=ex, 結果=rs)
    return out


def desc_stats(x, T, H, cal, w0):
    """描述用：E、中位、n、分群 CI（照 B1 的單位）；⛔ 不下判定。"""
    x = np.asarray(x, float); T = np.asarray(T, int); ok = np.isfinite(x); x, T = x[ok], T[ok]
    if len(x) == 0:
        return {"n": 0}
    o = {"n": int(len(x)), "E": float(x.mean()), "中位": float(np.median(x))}
    if H == 120 or len(x) < 2:
        return o
    g = (T - w0) // 60 if H == 60 else np.array([str(cal[t])[:7] for t in T])
    m, se, ng = XS.cr0(x, g)
    o.update(lo=m - 1.96 * se, hi=m + 1.96 * se, 群數=int(ng))
    return o


def fake_eval(acc):
    """acc (NCL, 2)：逐群 (n, ΣR) ⇒ E、CR0 SE（與 cr0 同式的彙總版）、n_eff、結果。"""
    nn = acc[:, 0]; S = acc[:, 1]; N = nn.sum()
    if N == 0:
        return None
    m = S.sum() / N
    se = float(np.sqrt(((S - nn * m) ** 2).sum()) / N)
    ng = int((nn > 0).sum()); n_eff = int(min(N, ng))
    ex, rs = XS.exit_result(m, m - 1.96 * se, m + 1.96 * se, int(N), n_eff)
    return {"n": int(N), "E": float(m), "lo": m - 1.96 * se, "hi": m + 1.96 * se, "n_eff": n_eff, "出口": ex, "結果": rs}


def sentence(g, H, J, x):
    nm = XS.SIG_NAME[g]
    must = "這是全市場跌破後的平均，不是對這一檔的預測。"
    pre = "樣本中等（n_eff＝{}，介於 30 與 100 之間）：".format(J["n_eff"]) if J["出口"] == "出口②" else ""
    if J["出口"] == "出口①":
        return "{}之後續抱 {} 天：樣本不足以分辨 ⇒ 不構成賣出理由（本件不支持因這個訊號而賣）。{}".format(nm, H, must)
    if J["結果"] == "結果③":
        warn = "⚠ 隨機挑日子也有 {}／30 次同樣是虧的。".format(x) if x >= 2 else ""
        return "{}{}{}之後，續抱 {} 天平均是虧的（{:+.2f}%，95% CI 上緣 {:+.2f}%）⇒ 隔天開盤賣掉比續抱好；賣一半則少虧一半。{}".format(
            warn, pre, nm, H, J["E"] * 100, J["hi"] * 100, must)
    what = "平均仍是賺的（{:+.2f}%）".format(J["E"] * 100) if J["結果"] == "結果②" else "分不出來（{:+.2f}%，95% CI {:+.2f}% ～ {:+.2f}%）".format(J["E"] * 100, J["lo"] * 100, J["hi"] * 100)
    return "{}{}之後續抱 {} 天{} ⇒ 不構成賣出理由（本件不支持因這個訊號而賣）。{}".format(pre, nm, H, what, must)


def ew_sell(O, okO, CFF, H):
    """EW_H(s) ＝ s 日 okO 的股票：CFF(s＋H−1)／O(s) − 1 的等權平均（B5）。"""
    n = O.shape[0]; out = np.full(n, np.nan); k = H - 1
    Od = np.where(okO[:n - k], O[:n - k], np.nan)
    r = CFF[k:] / Od - 1.0
    with np.errstate(invalid="ignore"):
        cnt = np.isfinite(r).sum(axis=1); s = np.nansum(r, axis=1)
    out[:n - k] = np.where(cnt > 0, s / np.maximum(cnt, 1), np.nan)
    return out


def load_universe(lim):
    stocks = pd.read_csv(os.path.join(H2.H2D, "meta", "stocks.csv"), dtype=str)
    U = UG.gate3(stocks)
    return U.head(lim) if lim else U


def run_pool(U, cal, w0, w1, off, mode, procs):
    """回 (逐檔結果, 假訊號臂累加 FA, FC)；假訊號臂陣列邊收邊加（⛔ 不逐檔留著，免得吃掉記憶體）。"""
    out = []; FA = None; FC = None
    with Pool(procs, initializer=_init, initargs=(cal, w0, w1, off, mode)) as pool:
        for r in pool.imap_unordered(work, list(zip(U["stock_id"], U["market"])), chunksize=4):
            if r is None:
                continue
            if "fake" in r:
                a = r.pop("fake"); c = r.pop("fake_cnt")
                FA = a if FA is None else FA + a; FC = c if FC is None else FC + c
            out.append(r)
    out.sort(key=lambda r: r["sid"])
    return out, FA, FC


def counts_table(res):
    tot = defaultdict(Counter)
    for r in res:
        for k, v in r["cnt"].items():
            tot[k].update(v)
    return tot


def acct(c):
    raw = sum(v for k, v in c.items() if k != "連鎖讀法會合併_但主讀法保留")
    return {"原始_窗內": int(raw), "剔除_K棒不足": int(c["剔除_K棒不足"]), "合併掉": int(c["合併掉"]), "剔除_硬斷點": int(c["剔除_硬斷點"]),
            "剔除_賣不掉": int(c["剔除_賣不掉"]), "剔除_超出日曆": int(c["剔除_超出日曆"]), "保留": int(c["保留"]),
            "另一讀法（對原始事件連鎖合併）會多合併的保留事件": int(c["連鎖讀法會合併_但主讀法保留"])}


# ═════════════ 開跑前報 ═════════════
def pre_report(res, cal, w0, w1, U):
    R = {"快照": SHA, "判定窗": [W0, W1], "gate3母體": int(len(U)), "可讀檔數": len(res),
         "時戳": pd.Timestamp.now(tz="Asia/Taipei").strftime("%Y-%m-%d %H:%M:%S"), "⛔": "本報不含任何報酬、價差或 R_H"}
    tot = counts_table(res)
    rows = pd.DataFrame([row for r in res for row in r["rows"]])
    K = rows[rows["狀態"] == "保留"]
    wdays = w1 - w0 + 1; wyears = (cal[w1] - cal[w0]).days / 365.25
    freq = {}; blocks = {}; defer = {}
    for g in XS.SIGS:
        for H in H_ALL:
            k = K[(K["rule"] == "close") & (K["g"] == g) & (K["H"] == H)]
            # 頻率
            tdy = wdays / wyears                                      # 每年交易日數（窗內交易日 ÷ 窗曆年）
            nk = k.groupby("sid").size()
            sy = {r["sid"]: r["expo"][H]["span"] / tdy for r in res}
            sy_s = pd.Series(sy); ev_s = nk.reindex(sy_s.index, fill_value=0)
            rate = ev_s / sy_s.where(sy_s > 0)
            big = sy_s >= 1
            mk = pd.Series({r["sid"]: r["market"] for r in res})
            f = {"合併母體比率_事件每股票年": float(ev_s.sum() / sy_s.sum()), "股票年": float(sy_s.sum()),
                 "曝露≥1年的股票": int(big.sum()), "每檔每年_平均": float(rate[big].mean()), "每檔每年_中位": float(rate[big].median()),
                 "每檔每年_p90": float(rate[big].quantile(0.9))}
            for mkt, nm in (("twse", "上市"), ("tpex", "上櫃")):
                sel = mk == mkt
                f[nm] = float(ev_s[sel].sum() / sy_s[sel].sum())
            yrs = {}
            cal_y = Counter(cal[w0:w1 - H + 1].year)
            for y in sorted(cal_y):
                num = int((pd.Series([cal[t].year for t in k["T"]]) == y).sum()) if len(k) else 0
                den = sum(r["expo"][H]["by_year"].get(y, 0) for r in res) / cal_y[y]
                yrs[str(y)] = {"事件": num, "股票年": round(den, 1), "每檔每年": num / den if den else None}
            f["逐年"] = yrs
            freq["{}_H{}".format(g, H)] = f
            # 區段數與可能出口
            T = k["T"].to_numpy(int); nn = len(T)
            months = len(np.unique([str(cal[t])[:7] for t in T])); b20 = len(np.unique((T - w0) // 20))
            b60 = len(np.unique((T - w0) // 60)); b120 = len(np.unique((T - w0) // 120))
            if H in (5, 10, 20):
                nb_ = months; unit = "曆月"; cap = len(np.unique([str(d)[:7] for d in cal[w0:w1 - H + 1]]))
            elif H == 60:
                nb_ = b60; unit = "60日區段"; cap = (w1 - H - w0) // 60 + 1
            else:
                nb_ = b120; unit = "120日區段"; cap = (w1 - H - w0) // 120 + 1
            ne = min(nn, nb_)
            exits = ("①②③ 都可能 ⇒ 判定" if ne >= 100 else ("只可能 ① 或 ②（到不了 ③）⇒ 判定；落 ② 句首加「樣本中等」" if ne >= 30 else "只可能出口① ⇒ 依構造不可判定"))
            blocks["{}_H{}".format(g, H)] = {"保留事件": nn, "分群單位": unit, "有事件的區段數": int(nb_), "理論上限": int(cap),
                                            "n_eff": int(ne), "20日區段數（另一讀法）": int(b20), "可能出口": exits if H != 120 else "依構造不可判定（描述）",
                                            "身分": "判定格" if H in H_JUDGE else "描述"}
            # 遞延
            dd = k["遞延天數"].to_numpy(int)
            defer["{}_H{}".format(g, H)] = {"保留事件": nn, "有遞延": int((dd > 0).sum()), "遞延原因": {kk: int(v) for kk, v in Counter(k.loc[k["遞延天數"] > 0, "遞延原因"]).items()},
                                           "遞延天數_平均（有遞延者）": float(dd[dd > 0].mean()) if (dd > 0).any() else 0.0,
                                           "遞延天數_最大": int(dd.max()) if nn else 0,
                                           "遞延天數分佈": {str(kk): int(v) for kk, v in sorted(Counter(dd[dd > 0]).items())},
                                           "終點狀態": {kk: int(v) for kk, v in Counter(k["終點"]).items()},
                                           "近似相等（|close−線|≤1e-9·線）": int(k["near_tie"].sum())}
    R["§七第一列_頻率（close 規則、保留事件）"] = freq
    R["§四_區段數與可能出口"] = blocks
    R["跌停／停牌遞延"] = defer
    R["事件帳"] = {"{}_{}_H{}".format(rule, g, H): acct(c) for (rule, g, H), c in sorted(tot.items())}
    R["下市狀態（delist_status）"] = dict(Counter(r["dstatus"] for r in res))
    stop = [k_ for k_, v in blocks.items() if k_.endswith("_H60") and v["有事件的區段數"] < 30]
    R["H60_實際區段<30而停"] = stop
    return R, K


# ═════════════ 主程式 ═════════════
def setup(argv):
    procs = int(argv[argv.index("--procs") + 1]) if "--procs" in argv else 2
    lim = int(argv[argv.index("--limit") + 1]) if "--limit" in argv else None
    cal = D.load_calendar()
    w0 = int(cal.searchsorted(pd.Timestamp(W0))); w1 = int(cal.searchsorted(pd.Timestamp(W1)))
    assert str(cal[w0].date()) == W0 and str(cal[w1].date()) == W1 and w1 - w0 + 1 == WIN_DAYS
    U = load_universe(lim); off = TR.load_official()
    return procs, lim, cal, w0, w1, U, off


def main_pre(argv):
    import selftest_exit_signal as STX
    t0 = time.time(); STX.run_all()
    procs, lim, cal, w0, w1, U, off = setup(argv)
    print("[資料] 快照 {}｜判定窗 [{}, {}]｜gate3 {:,} 檔｜pre（⛔ 不算報酬）".format(SHA[:10], W0, W1, len(U)), flush=True)
    res, _, _ = run_pool(U, cal, w0, w1, off, "pre", procs)
    print("[讀檔＋偵測] {:,} 檔｜{:.0f}s".format(len(res), time.time() - t0), flush=True)
    R, _ = pre_report(res, cal, w0, w1, U)
    os.makedirs(OUT, exist_ok=True)
    json.dump(R, open(os.path.join(OUT, "pre_run.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    print(json.dumps({k: R[k] for k in ("§四_區段數與可能出口", "H60_實際區段<30而停")}, ensure_ascii=False, indent=1, default=str))
    print("完成 {:.0f}s".format(time.time() - t0))


def main_body(argv):
    import selftest_exit_signal as STX
    t0 = time.time()
    print("[時點] 本體開跑 {}".format(time.strftime("%F %T")), flush=True)
    fx = STX.run_all()
    procs, lim, cal, w0, w1, U, off = setup(argv)
    pre = json.load(open(os.path.join(OUT, "pre_run.json"), encoding="utf-8"))
    assert not pre["H60_實際區段<30而停"], "⛔ 開跑前報 H60 < 30 段 ⇒ 停"
    res, FA, FC = run_pool(U, cal, w0, w1, off, "body", procs)
    print("[讀檔＋偵測＋假訊號] {:,} 檔｜{:.0f}s".format(len(res), time.time() - t0), flush=True)
    R_pre, _ = pre_report(res, cal, w0, w1, U)
    same_pre = {k: R_pre[k] for k in ("§四_區段數與可能出口", "事件帳")} == {k: pre[k] for k in ("§四_區段數與可能出口", "事件帳")}
    print("[查核0] 本體重數的事件帳與區段數 ＝ 開跑前報：{}".format(same_pre), flush=True)
    assert same_pre, "⛔ 本體事件帳與開跑前報不同"
    sids = [r["sid"] for r in res]; sidx = {s: i for i, s in enumerate(sids)}
    rows = pd.DataFrame([row for r in res for row in r["rows"]])
    K = rows[rows["狀態"] == "保留"].copy()
    K["T_date"] = [str(cal[t].date()) for t in K["T"]]; K["s_date"] = [str(cal[t].date()) for t in K["s"]]
    K["end_date"] = [str(cal[int(t)].date()) for t in K["j_end"]]
    K["month"] = [str(cal[t])[:7] for t in K["T"]]; K["blk60"] = (K["T"] - w0) // 60; K["year"] = [cal[t].year for t in K["T"]]
    # 基準
    O = np.column_stack([r["o"] for r in res]); CFF = np.column_stack([r["cff"] for r in res])
    okO = np.isfinite(O) & (O > 0) & np.isfinite(CFF)
    EW = {H: ew_sell(O, okO, CFF, H) for H in H_ALL}
    del O, CFF
    s50 = D.load_stock("0050", "twse", cal).df
    o50 = s50["open"].to_numpy(float); c50 = pd.Series(s50["close"].to_numpy(float)).ffill().to_numpy()
    K["EW"] = [EW[H][s] for H, s in zip(K["H"], K["s"])]
    K["X"] = K["R"] - K["EW"]
    K["r0050"] = [c50[s + H - 1] / o50[s] - 1.0 - BUY_0050 if np.isfinite(o50[s]) else np.nan for H, s in zip(K["H"], K["s"])]
    K["換0050減續抱"] = K["r0050"] - K["R"]
    # 門檻B（B6 c）
    import ref_interval as RI
    _, _, sigB, _, _, _, _ = RI.load_all()
    gb = defaultdict(list)
    for s_, e_ in zip(sigB["sid"], sigB["entry_pos"]):
        gb[s_].append(int(e_))
    gb = {k: np.array(sorted(v)) for k, v in gb.items()}
    def in_b(sid, T):
        a = gb.get(sid)
        if a is None:
            return False
        k = np.searchsorted(a, T, side="right") - 1
        return bool(k >= 0 and T <= a[k] + 119)
    K["門檻B後120日內"] = [in_b(s, t) for s, t in zip(K["sid"], K["T"])]
    t_first = time.strftime("%F %T")
    print("[時點] 本體第一次彙總報酬 {}｜{:.0f}s".format(t_first, time.time() - t0), flush=True)
    RES = {"快照": SHA, "判定窗": [W0, W1], "gate3母體": int(len(U)), "可讀檔數": len(res),
           "時點": {"本體第一次彙總報酬": t_first}, "fixture": fx}
    tot = counts_table(res)
    # 假訊號臂合計
    # ── 6 格
    CL = K[K["rule"] == "close"]
    J = {}; fake = {}
    for gi, g in enumerate(XS.SIGS):
        for hi, H in enumerate(H_JUDGE):
            k = CL[(CL["g"] == g) & (CL["H"] == H)]
            s_ = cell_stats(k["R"], k["T"], H, cal, w0)
            fr = [fake_eval(FA[r, gi, hi]) for r in range(REPS)]
            fr = [f for f in fr if f]
            x3 = sum(1 for f in fr if f["結果"] == "結果③")
            fE = float(np.mean([f["E"] for f in fr]))
            fake["{}_H{}".format(g, H)] = {"x／30（落結果③）": x3, "次數": len(fr), "假訊號日平均E": fE,
                                          "假E範圍": [float(min(f["E"] for f in fr)), float(max(f["E"] for f in fr))],
                                          "CI不含0次數": sum(1 for f in fr if not (f["lo"] <= 0 <= f["hi"])),
                                          "結果分佈": dict(Counter(f["結果"] for f in fr)),
                                          "平均n": float(np.mean([f["n"] for f in fr])), "平均n_eff": float(np.mean([f["n_eff"] for f in fr])),
                                          "帳（30次合計：抽出、合併、剔除、可抽日不足）": [int(v) for v in FC[:, gi, hi].sum(axis=0)],
                                          "真E−假E": s_["E"] - fE, "逐次": fr}
            dd = k["遞延天數"].to_numpy(int)
            J["{}_H{}".format(g, H)] = {**s_, "事件帳": acct(tot[("close", g, H)]),
                                       "遞延": {"有遞延": int((dd > 0).sum()), "遞延原因": dict(Counter(k.loc[k["遞延天數"] > 0, "遞延原因"])),
                                              "讀法①另一種（從排程 T＋1 起算）會受影響的筆數": int((dd > 0).sum())},
                                       "終點狀態": dict(Counter(k["終點"])),
                                       "假訊號": {kk: v for kk, v in fake["{}_H{}".format(g, H)].items() if kk != "逐次"},
                                       "對照①_超額（R−gate3等權同段）": desc_stats(k["X"], k["T"], H, cal, w0),
                                       "對照②_換成0050減續抱（已扣0.1425%）": desc_stats(k["換0050減續抱"], k["T"], H, cal, w0)}
            J["{}_H{}".format(g, H)]["給使用者的句子"] = sentence(g, H, J["{}_H{}".format(g, H)], x3)
            print("[{} H{}] n {:,}｜n_eff {}｜E {:+.3f}%（CI {:+.3f} ～ {:+.3f}）｜{} {}｜假訊號 x＝{}／30、假E {:+.3f}%".format(
                g, H, s_["n"], s_["n_eff"], s_["E"] * 100, s_["lo"] * 100, s_["hi"] * 100, s_["出口"], s_["結果"], x3, fE * 100), flush=True)
    RES["判定6格"] = J
    RES["假訊號臂逐次"] = {k: v["逐次"] for k, v in fake.items()}
    # 合句（同訊號兩個 H 結論不同 ⇒ 兩句都寫）
    RES["同訊號兩H"] = {g: {"H20": J[g + "_H20"]["結果"], "H60": J[g + "_H60"]["結果"],
                        "結論相同": J[g + "_H20"]["結果"] == J[g + "_H60"]["結果"]} for g in XS.SIGS}
    # ── 必報
    must = {}
    # H120 與描述臂 b（H5、H10）
    h120 = {}; hb = {}
    for g in XS.SIGS:
        k = CL[(CL["g"] == g) & (CL["H"] == 120)]
        h120[g] = {**cell_stats(k["R"], k["T"], 120, cal, w0), "事件帳": acct(tot[("close", g, 120)])}
        for H in (5, 10):
            k = CL[(CL["g"] == g) & (CL["H"] == H)]
            hb["{}_H{}".format(g, H)] = {**desc_stats(k["R"], k["T"], H, cal, w0), "事件帳": acct(tot[("close", g, H)])}
    must["H120_描述（依構造不可判定）"] = h120
    must["描述臂b_H5_H10"] = hb
    # 描述臂 a
    va = {}
    for rule, nm in (("pct1", "跌破1%"), ("d3", "連3日收在線下")):
        for g in XS.SIGS:
            for H in H_VAR:
                k = K[(K["rule"] == rule) & (K["g"] == g) & (K["H"] == H)]
                va["{}_{}_H{}".format(nm, g, H)] = {**desc_stats(k["R"], k["T"], H, cal, w0), "事件帳": acct(tot[(rule, g, H)])}
    must["描述臂a"] = va
    # 兩兩同日重疊（H20 保留事件）
    key = {g: set(zip(CL.loc[(CL["g"] == g) & (CL["H"] == 20), "sid"], CL.loc[(CL["g"] == g) & (CL["H"] == 20), "T"])) for g in XS.SIGS}
    near = {g: defaultdict(list) for g in XS.SIGS}
    for g in XS.SIGS:
        for s, t in key[g]:
            near[g][s].append(t)
        near[g] = {s: np.array(sorted(v)) for s, v in near[g].items()}
    ov = {}
    for i, a in enumerate(XS.SIGS):
        for b in XS.SIGS[i + 1:]:
            both = key[a] & key[b]
            def within(A, B):
                q = 0
                for s, t in key[A]:
                    arr = near[B].get(s)
                    if arr is not None and np.min(np.abs(arr - t)) <= 5:
                        q += 1
                return q
            ov["{}×{}".format(a, b)] = {"同檔同日": len(both), "÷{}".format(a): len(both) / len(key[a]), "÷{}".format(b): len(both) / len(key[b]),
                                        "±5日內_÷{}".format(a): within(a, b) / len(key[a]), "±5日內_÷{}".format(b): within(b, a) / len(key[b])}
    must["三訊號兩兩同日重疊（H20保留事件）"] = ov
    # 分組 a～d
    grp = {}
    for g in XS.SIGS:
        for H in H_JUDGE:
            k = CL[(CL["g"] == g) & (CL["H"] == H)].copy()
            k["三分位"] = pd.qcut(k["pre60"].rank(method="first"), 3, labels=["低", "中", "高"])
            e = {}
            for q in ("低", "中", "高"):
                kk = k[k["三分位"] == q]
                e[q] = {**desc_stats(kk["R"], kk["T"], H, cal, w0), "pre60範圍": [float(kk["pre60"].min()), float(kk["pre60"].max())]}
            lb = {q: desc_stats(k.loc[k["label"] == q, "R"], k.loc[k["label"] == q, "T"], H, cal, w0) for q in ("偏漲", "盤整", "偏跌")}
            gbq = {str(q): desc_stats(k.loc[k["門檻B後120日內"] == q, "R"], k.loc[k["門檻B後120日內"] == q, "T"], H, cal, w0) for q in (True, False)}
            mk = {nm: desc_stats(k.loc[k["market"] == m_, "R"], k.loc[k["market"] == m_, "T"], H, cal, w0) for m_, nm in (("twse", "上市"), ("tpex", "上櫃"))}
            yr = {str(y): desc_stats(k.loc[k["year"] == y, "R"], k.loc[k["year"] == y, "T"], H, cal, w0) for y in sorted(k["year"].unique())}
            grp["{}_H{}".format(g, H)] = {"a_跌破前60日報酬三分位": e, "b_狀態標籤": lb, "c_門檻B進場後120日內": gbq, "d_上市上櫃": mk, "d_逐年": yr}
    must["分組"] = grp
    # 放棄組
    ab = {}
    for g in XS.SIGS:
        for H in H_JUDGE:
            k = CL[(CL["g"] == g) & (CL["H"] == H)]
            p90 = float(np.percentile(k["R"], 90)); top = k[k["R"] >= p90]; rest = k[k["R"] < p90]
            def prof(d):
                return {"n": int(len(d)), "平均R": float(d["R"].mean()), "pre60_中位": float(d["pre60"].median()), "pre60_平均": float(d["pre60"].mean()),
                        "pre20_中位": float(d["pre20"].median()), "離線_中位": float(d["dist"].median()), "MA20斜率_中位": float(d["ma20_slope"].median()),
                        "狀態標籤": {q: float((d["label"] == q).mean()) for q in ("偏漲", "盤整", "偏跌")},
                        "上櫃比例": float((d["market"] == "tpex").mean()), "門檻B後120日內比例": float(d["門檻B後120日內"].mean())}
            ab["{}_H{}".format(g, H)] = {"p90門檻": p90, "續抱最後大漲（R≥p90）": prof(top), "其餘": prof(rest)}
    must["放棄組_賣掉會錯過哪種"] = ab
    # 近似相等、連鎖讀法
    must["近似相等件數（保留事件）"] = {"{}_H{}".format(g, H): int(CL.loc[(CL["g"] == g) & (CL["H"] == H), "near_tie"].sum()) for g in XS.SIGS for H in H_ALL}
    # ⚠ 修正（2026-09-25 20:0x）：原寫 ~CL["near_tie"]（object 欄取反 ⇒ 沒剔到任何一筆）；19:53 產出的 summary.json 此欄為修正前版本，
    #    以 researchExit_tiesens.py 的 tie_sensitivity.json 為準（判定 6 格不受影響：這一欄只是描述）。
    nt = CL["near_tie"].astype(bool)
    must["敏感度_剔除近似相等事件後（描述）"] = {"{}_H{}".format(g, H): desc_stats(
        CL.loc[(CL["g"] == g) & (CL["H"] == H) & ~nt, "R"], CL.loc[(CL["g"] == g) & (CL["H"] == H) & ~nt, "T"], H, cal, w0)
        for g in XS.SIGS for H in H_JUDGE}
    RES["必報"] = must
    # ── 0050 描述臂③
    P = prep("0050", "twse", cal, off)
    ev, LN = events_of(P)
    e50 = {}
    rows50 = []
    for g in XS.SIGS:
        for H in (20, 60, 120):
            st = XS.statuses(ev[("close", g)], H, P["X"], w0, w1)
            kk = [q for q in st if q["狀態"] == "保留"]
            x = [XS.ret(P["o"], P["c"], q["s"], q["j_end"]) for q in kk]; T = [q["T"] for q in kk]
            s_ = cell_stats(x, T, H, cal, w0) if len(x) else {"n": 0}
            if H != 120 and len(x):
                s_["出口"], s_["結果"] = (s_["出口"], s_["結果"]) if s_["n_eff"] >= 30 else ("出口①", "樣本不足以分辨")
            e50["{}_H{}".format(g, H)] = {**s_, "事件帳": dict(Counter(q["狀態"] for q in st))}
            for q, r_ in zip(kk, x):
                rows50.append({"g": g, "H": H, "T_date": str(cal[q["T"]].date()), "s_date": str(cal[q["s"]].date()), "R": r_, "遞延天數": q["遞延天數"]})
    RES["0050描述臂③"] = {"說明": "只答「手上的 0050 跌破後續抱 vs 賣」；⛔ 不判、⛔ 不計 N；00631L 參考 0050 描述臂、未另測；00757、00910 無法判定",
                         "格": e50}
    pd.DataFrame(rows50).to_csv(os.path.join(OUT, "events_0050.csv"), index=False, encoding="utf-8")
    # ── 逐筆檔
    cols = ["sid", "market", "rule", "g", "H", "T", "T_date", "s", "s_date", "j_end", "end_date", "遞延天數", "遞延原因", "終點",
            "line", "line_prev", "cT", "cTm1", "near_tie", "P_s", "P_end", "R", "EW", "X", "r0050", "換0050減續抱",
            "pre60", "pre20", "dist", "ma20_slope", "label", "門檻B後120日內", "month", "blk60", "year", "連鎖"]
    K[cols].to_csv(os.path.join(OUT, "events_kept.csv.gz"), index=False)
    rows[rows["狀態"] != "保留"].assign(T_date=lambda d: [str(cal[t].date()) for t in d["T"]]).to_csv(
        os.path.join(OUT, "events_excluded.csv.gz"), index=False)
    # ── 查核用：抽 20 筆（6 格）
    rng = np.random.default_rng(SEED_FAKE)
    J6 = CL[CL["H"].isin(H_JUDGE)].reset_index(drop=True)
    ii = rng.choice(len(J6), size=20, replace=False)
    J6.iloc[ii][cols].to_csv(os.path.join(OUT, "hand_pick20.csv"), index=False, encoding="utf-8")
    RES["時點"]["本體完成"] = time.strftime("%F %T")
    json.dump(RES, open(os.path.join(OUT, "summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    print("完成 {:.0f}s".format(time.time() - t0))


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "pre"
    if mode == "pre":
        main_pre(sys.argv)
    elif mode == "body":
        main_body(sys.argv)
    else:
        raise SystemExit("用法：researchExit.py pre|body [--procs 2] [--limit N]")

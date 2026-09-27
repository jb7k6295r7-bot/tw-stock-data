# -*- coding: utf-8 -*-
"""PREREG強勢類股（先找最強類股、再在裡面挑股票）。判準＝台股策略線 強勢類股 登錄 seq1（sha bb1c8b224f5bb587，2026-09-27 17:08）；
裁定 seq240、seq241、seq242、seq245（發號、N_組合 ＋1）。

    python -m backtest.researchSector pre [--procs 2]      pre 段（⛔ 不讀換股日之後的價格；讀法為當時的暫定 P1～P6，面板 resultsAFC）
    python -m backtest.researchSector selftest              模擬器 fixture（常數價只剩成本／已知報酬／續抱 vs 全賣全買成本差／漲跌停／下市）
    python -m backtest.researchSector body [--procs 2]     本體（12 處未列預設照暫定 (i) 全部定案，回測線協調 2026-09-27）

⭐ 12 處未列預設的定案值（本體用；PRE_REPORT.md §二）：
 U1 (i) 換股日仍入選的舊持股續抱、只賣落選、買新入選、⛔ 不再平衡等權（主版）；(ii) 全賣全買另報成本敏感度（只描述）
 U2 (i) 抱 60 日 ＝ 每月換股日買一批、各抱 60 個交易日（出場 ＝ 進場後第 59 個交易日收盤）、10 槽滿了就不買（simulate_mtm、tradable＋delist）
 U3 (i) 季換 ＝ 1、4、7、10 月的換股日（其餘同月換主版）
 U4 (i) eligible ＝ 同月第一個交易日量測的 W1 eligible；面板改用 backtest/resultsp9_engine/panel_ext.csv.gz（commit d2c9df7fe2，
        同一支 build_panel，量測日到 2026-08-03）；⛔ 先對帳 2026-03-02 以前 eligible 與 resultsAFC 面板逐列相同，不同就停
 U5 (i) 產業別用今日快照（2022 新增類別往回套）：data/meta/industry.csv；金融保險業／金融業 ⇒ 金融保險；存託憑證排除
 U6 (i) 已下市股沒有類股、無法入選（⇒ 登錄「含已下市股」做不到這一部分，照實寫）
 U7 (i) 類股強度 ＝ 成分股（當月 eligible 且有類股、L 日報酬有限）各自 L 日報酬（ffill 還原收盤，截至換股日前一交易日）的等權平均；成分 ＜ 5 ⇒ 不排名
 U8 (i) (a)(b) 的前 10 檔在前 k 強類股的【聯集】裡一起排；同值依代號
 U9 (i) 現金報酬 0
 U10 (i) (c) 與假訊號臂 default_rng(20260925＋r)，r ＝ 0…999
 U11 (i) 探索段挑格平手 ⇒ 年化高者、再 L 小、k 小、(a) 先
 U12 早年段依構造做不了（data/early 沒有全體個股還原事件 TWT49U 與個股法人 inst_ok）⇒ 寫明、不跑
⚠ 查核抓到：industry.csv 有 40 列名稱空白（代碼 32 文化創意業 26 檔、33 農業科技 4 檔、91 存託憑證 10 檔）；pre 段把它們併成同一個 NaN 類股
   （⛔ 不是 U5 的「照原名」）。pre 的檔案保持原樣、⛔ 不重跑；本體依代碼補名稱（CODE_NAME）。
 其餘沿用 pre 的 P5（營收 24 月新高 ＝ p4_features.rev_hi24_flags 在換股日 ＝ 100）、P6（換手 ＝ 新買進檔數 ÷ 10）。

主版模擬器（U1 (i)，本檔 sim_book；⭐ 與 simulate_mtm 同一套成交／成本口徑）：
 ・換股日 e：落選者標「待賣」⇒ 當日開盤賣（要有成交、開盤有限 > 0、開盤不是跌停）；賣不掉 ⇒ 之後第一個可成交日開盤賣；
   待賣期間照 ffill 收盤計值、仍占槽位；之後再也沒成交且 delist_status 為 delisted_* ⇒ 以最後收盤了結；ambig ⇒ 照停牌、逐筆報數
 ・成本：賣出時扣「進場金額 × 0.585%」（＝ simulate_mtm：cash += amt × (1 + gross − COST)）；買進不扣
 ・新入選依名次在當日開盤買（要有成交、開盤有限 > 0、開盤不是漲停）；金額 ＝ min(前一日收盤 equity ÷ 10, 現金)；
   空槽 ＝ 10 − 持有（含待賣）；買不到 ⇒ 該名額持現金、⛔ 不遞補下一名
 ・逐日 equity ＝ 現金 ＋ Σ 股數 × ffill 收盤；段落指標 ＝ research13.window_stats（245 日／年）在連續一條權益上切段
"""
from __future__ import annotations
import os, sys, time, json
from collections import Counter
from multiprocessing import Pool
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
import researchH2 as H2
D, TR, UG = H2.D, H2.TR, H2.UG
from backtest import research34 as R34
from backtest import p4_features as P4F

OUT = "backtest/resultsSector"
LS, KS, PICKS = (20, 60, 120), (1, 3, 5), ("a", "b")
MIN_MEM, N = 5, 10
SEG = {"探索": ("2017-03-02", "2021-12-30"), "確認": ("2022-01-03", "2026-08-24")}
NAME_MAP = {"金融業": "金融保險", "金融保險業": "金融保險", "金融保險": "金融保險"}
_G = {}


def _init(cal):
    _G.update(cal=cal)


def load_close(args):
    sid, mk = args
    st = D.load_stock(sid, mk, _G["cal"])
    if st is None:
        return sid, None
    return sid, pd.Series(st.df["close"].to_numpy(float)).ffill().to_numpy(np.float32)


def main_pre():
    t0 = time.time()
    procs = int(sys.argv[sys.argv.index("--procs") + 1]) if "--procs" in sys.argv else 2
    cal = D.load_calendar(); n = len(cal)
    stocks = pd.read_csv(os.path.join(H2.H2D, "meta", "stocks.csv"), dtype=str)
    G = UG.gate3(stocks)
    ind = pd.read_csv(os.path.join(H2.H2D, "meta", "industry.csv"), dtype=str)
    ind = ind[ind["industry_name"] != "存託憑證"]
    cls = {s: NAME_MAP.get(nm, nm) for s, nm in zip(ind["stock_id"], ind["industry_name"])}
    panel = pd.read_csv("backtest/resultsAFC/panel.csv.gz", dtype={"stock_id": str}, usecols=["measure_date", "stock_id", "market", "eligible"],
                        parse_dates=["measure_date"])
    rev, _, _ = R34.load_revenue()
    rf = P4F.rev_hi24_flags(rev, cal)
    rd = R34.rebalance_dates(list(rev.index), cal, 10)
    reb = sorted({e for _, e in rd.values() if cal[e] >= pd.Timestamp("2016-08-01") and e < n})
    with Pool(procs, initializer=_init, initargs=(cal,)) as pool:
        C = dict(pool.map(load_close, list(zip(G["stock_id"], G["market"])), chunksize=16))
    C = {s: v for s, v in C.items() if v is not None}
    print("[資料] gate3 {:,}｜有價 {:,}｜有類股 {:,}｜換股日 {} 個（{}～{}）｜{:.0f}s".format(len(G), len(C), sum(s in cls for s in C), len(reb),
          cal[reb[0]].date(), cal[reb[-1]].date(), time.time() - t0), flush=True)
    delisted = set(pd.read_csv(os.path.join(H2.H2D, "meta", "delisted.csv"), dtype=str)["stock_id"]) if os.path.exists(os.path.join(H2.H2D, "meta", "delisted.csv")) else set()
    pm = {d: g for d, g in panel.groupby("measure_date")}
    meas = sorted(pm)
    rows = []; cov = []
    picks = {}
    for e in reb:
        d = cal[e]; mm = [m for m in meas if m.year == d.year and m.month == d.month]; md = max(mm) if mm else pd.NaT
        rowf = rf.iloc[e]
        if pd.isna(md):
            continue
        el = pm[md]; el = el[el["eligible"].astype(bool)]["stock_id"].tolist()
        el = [s for s in el if s in C]
        nocls = [s for s in el if s not in cls]
        cov.append({"換股日": str(d.date()), "eligible": len(el), "無類股": len(nocls), "無類股且已下市": sum(s in delisted for s in nocls)})
        t = e - 1
        for L in LS:
            if t - L < 0:
                continue
            r = {s: float(C[s][t] / C[s][t - L] - 1.0) for s in el if s in cls and np.isfinite(C[s][t]) and np.isfinite(C[s][t - L]) and C[s][t - L] > 0}
            mem = {}
            for s in r:
                mem.setdefault(cls[s], []).append(s)
            strength = {c: np.mean([r[s] for s in m]) for c, m in mem.items() if len(m) >= MIN_MEM}
            order = sorted(strength, key=lambda c: (-strength[c], c))
            for k in KS:
                top = order[:k]
                uni = [s for c in top for s in mem[c]]
                for pk in PICKS:
                    cand = uni if pk == "a" else [s for s in uni if s in rowf.index and rowf[s] == 100]
                    sel = sorted(cand, key=lambda s: (-r[s], s))[:N]
                    picks.setdefault((L, k, pk), []).append((e, sel, Counter(cls[s] for s in sel), len(strength)))
    RES = {"性質": "PREREG強勢類股 pre（⛔ 未讀換股日之後的價格；讀法 P1～P6 為暫定）", "快照": H2.SHA, "換股日數": len(reb),
           "類股覆蓋": {"eligible中位": float(np.median([c["eligible"] for c in cov])), "無類股中位": float(np.median([c["無類股"] for c in cov])),
                    "無類股占eligible（全期股月）": sum(c["無類股"] for c in cov) / max(1, sum(c["eligible"] for c in cov)),
                    "無類股且已下市（全期股月）": sum(c["無類股且已下市"] for c in cov)},
           "類股數": {"industry.csv類股（去存託憑證、上市櫃對齊後）": len(set(cls.values()))}, "格": {}}
    for (L, k, pk), lst_ in picks.items():
        for seg, (a, b) in SEG.items():
            sub = [x for x in lst_ if pd.Timestamp(a) <= cal[x[0]] <= pd.Timestamp(b)]
            if not sub:
                continue
            nh = [len(x[1]) for x in sub]
            conc = [max(x[2].values()) / len(x[1]) for x in sub if x[1]]
            tov = [len(set(y[1]) - set(x[1])) / N for x, y in zip(sub[:-1], sub[1:])]
            RES["格"]["L{}_k{}_{}_{}".format(L, k, pk, seg)] = {"換股次數": len(sub), "平均持股檔數": float(np.mean(nh)), "現金比例（依構造）": float(1 - np.mean(nh) / N),
                                                            "持股 0 檔的月數": int(sum(1 for v in nh if v == 0)),
                                                            "類股集中度_平均": float(np.mean(conc)) if conc else None, "類股集中度_最大": float(np.max(conc)) if conc else None,
                                                            "每月換手_平均": float(np.mean(tov)) if tov else None, "可排名類股數_中位": float(np.median([x[3] for x in sub]))}
    os.makedirs(OUT, exist_ok=True)
    pd.DataFrame(cov).to_csv(os.path.join(OUT, "pre_coverage.csv"), index=False)
    json.dump(RES, open(os.path.join(OUT, "pre.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    print(json.dumps({k: v for k, v in RES.items() if k != "格"}, ensure_ascii=False, indent=1, default=float))
    for k_, v in RES["格"].items():
        print(k_, {kk: (round(vv, 3) if isinstance(vv, float) else vv) for kk, vv in v.items()})
    print("pre 完成 {:.0f}s".format(time.time() - t0))


# ═════════════════════════════ 本體 ═════════════════════════════
from backtest import research13 as R13
from backtest import research11 as R

COST = H2.COST_RT
SEED0, REPS = 20260925, 1000
PANEL_EXT = "backtest/resultsp9_engine/panel_ext.csv.gz"
PANEL_AFC = "backtest/resultsAFC/panel.csv.gz"
RECON_TO = pd.Timestamp("2026-03-02")
W0, W1 = "2017-03-02", "2026-08-24"
CODE_NAME = {"32": "文化創意業", "33": "農業科技", "91": "存託憑證"}     # 櫃買／證交所產業代碼（industry.csv 名稱空白的三個代碼）


def load_full(args):
    """一檔：ffill 還原收盤（float64）、還原開盤、tradability 四旗標。"""
    sid, mk = args
    cal = _G["cal"]
    st = D.load_stock(sid, mk, cal)
    if st is None:
        return sid, None
    c = pd.Series(st.df["close"].to_numpy(float)).ffill().to_numpy(float)
    o = st.df["open"].to_numpy(float)
    tb = TR.one(sid, cal)
    return sid, {"c": c, "o": o, "trd": tb["trd"], "up_o": tb["up_o"], "dn_o": tb["dn_o"], "dn_c": tb["dn_c"]}


def sim_book(sel_by_e: dict, P: dict, dl: dict, t0: int, t1: int, mode: str = "hold", n_slots: int = N, record: bool = False):
    """U1 主版模擬器（mode "hold" ＝ (i) 續抱；"all" ＝ (ii) 全賣全買）。sel_by_e：換股日位置 → 依名次排好的名單。
    回傳 equity（長度 ncal；t0 之前 ＝ 1、t1 之後 ＝ equity[t1]）、逐日持股數與現金比例、每次換股的買進檔數與換股後持股、計數。"""
    ncal = len(next(iter(P.values()))["c"])
    eq = np.ones(ncal); cash = 1.0
    pos = {}                     # sid → [units, amt]
    pend = set()
    npos = np.zeros(ncal, np.int16); cashf = np.zeros(ncal)
    buys = {}; hold_after = {}; held_days = [] if record else None
    cnt = {"buy": 0, "sell": 0, "buy_blocked_limit_up": 0, "buy_blocked_halt": 0, "sell_delayed_days": 0, "delist_settled": 0,
           "delist_ambig_days": 0, "cost_paid": 0.0}
    for t in range(t0, t1 + 1):
        sel = sel_by_e.get(t)
        if sel is not None:
            if mode == "all":
                pend = set(pos)
            else:
                pend = (pend | (set(pos) - set(sel))) - set(sel)
        # ── 賣（開盤）
        for s in sorted(pend):
            x = P[s]; o_t = x["o"][t]
            if x["trd"][t] and not x["dn_o"][t] and np.isfinite(o_t) and o_t > 0:
                px = o_t
            elif (not x["trd"][t]) and s in dl and t > dl[s]["last"] and dl[s]["status"].startswith("delisted"):
                px = x["c"][t]; cnt["delist_settled"] += 1               # 下市 ⇒ 以最後收盤了結（ffill 收盤 ＝ 最後收盤）
            else:
                cnt["sell_delayed_days"] += 1
                if (not x["trd"][t]) and s in dl and t > dl[s]["last"]:
                    cnt["delist_ambig_days"] += 1
                continue
            u, amt = pos.pop(s)
            cash += u * px - amt * COST; cnt["cost_paid"] += amt * COST; cnt["sell"] += 1
            pend.discard(s)
        # ── 買（開盤）
        if sel is not None:
            free = n_slots - len(pos)
            new = [s for s in sel if s not in pos][:max(free, 0)]
            nb = 0
            for s in new:
                x = P[s]; o_t = x["o"][t]
                if not x["trd"][t] or not (np.isfinite(o_t) and o_t > 0):
                    cnt["buy_blocked_halt"] += 1; continue
                if x["up_o"][t]:
                    cnt["buy_blocked_limit_up"] += 1; continue
                amt = min(eq[t - 1] / n_slots, cash)
                if amt <= 1e-12:
                    break
                cash -= amt; pos[s] = [amt / o_t, amt]; nb += 1; cnt["buy"] += 1
            buys[t] = nb; hold_after[t] = sorted(pos)
        hv = 0.0
        for s, (u, _) in pos.items():
            hv += u * P[s]["c"][t]
        eq[t] = cash + hv
        npos[t] = len(pos); cashf[t] = cash / eq[t] if eq[t] > 0 else np.nan
        if record:
            held_days.append(frozenset(pos))
    eq[t1 + 1:] = eq[t1]
    return {"eq": eq, "npos": npos, "cashf": cashf, "buys": buys, "hold": hold_after, "cnt": cnt, "held_days": held_days}


def seg_metrics(eq, a, b):
    c, m = R13.window_stats(eq, 0, len(eq), a, b + 1)
    return float(c), float(m), (float(c) / abs(float(m)) if m < 0 else float("nan"))


def label(c, m, c0, m0):
    r, r0 = c / abs(m), c0 / abs(m0)
    if c > c0 and r >= r0:
        return "合格"
    if c > c0:
        return "另列"
    return "不合格"


class Book:
    """每個換股日的排名素材（⛔ 只用換股日前一交易日以前的收盤、換股日可得的營收旗標、同月量測的 eligible）。"""

    def __init__(self, reb, cal, P, cls, elig_by_e, revset):
        self.reb, self.cal, self.P, self.cls = reb, cal, P, cls
        self.M = {}
        for e in reb:
            el = elig_by_e[e]; t = e - 1
            for L in LS:
                r = {}
                for s in el:
                    if s not in cls:
                        continue
                    c = P[s]["c"]; a_, b_ = c[t - L], c[t]
                    if np.isfinite(a_) and np.isfinite(b_) and a_ > 0:
                        r[s] = float(b_ / a_ - 1.0)
                mem = {}
                for s in sorted(r):
                    mem.setdefault(cls[s], []).append(s)
                strength = {c_: float(np.mean([r[s] for s in m])) for c_, m in mem.items() if len(m) >= MIN_MEM}
                order = sorted(strength, key=lambda c_: (-strength[c_], c_))
                self.M[(e, L)] = (r, mem, order, strength)
        self.rev = revset

    def pick(self, e, L, k, pk, rng=None, fake=False):
        r, mem, order, _ = self.M[(e, L)]
        if fake:
            idx = rng.choice(len(order), size=k, replace=False)
            top = [order[i] for i in idx]
        else:
            top = order[:k]
        uni = [s for c_ in top for s in mem[c_]]
        if pk == "c":
            m = min(N, len(uni))
            return [uni[i] for i in rng.choice(len(uni), size=m, replace=False)] if m else []
        cand = uni if pk == "a" else [s for s in uni if s in self.rev[e]]
        return sorted(cand, key=lambda s: (-r[s], s))[:N]


def cell_stats(res, seg_ab, reb_seg, cls, first_reb):
    a, b = seg_ab
    c, m, ratio = seg_metrics(res["eq"], a, b)
    tv = [res["buys"][e] / N for e in reb_seg if e != first_reb]
    conc = []
    for e in reb_seg:
        h = res["hold"][e]
        if h:
            conc.append(max(Counter(cls[s] for s in h).values()) / len(h))
    return {"年化": c, "回落": m, "比值": ratio, "每月換手": float(np.mean(tv)) if tv else float("nan"),
            "平均持股": float(np.mean(res["npos"][a:b + 1])), "現金比例": float(np.nanmean(res["cashf"][a:b + 1])),
            "集中度_平均": float(np.mean(conc)) if conc else float("nan"), "集中度_最大": float(np.max(conc)) if conc else float("nan"),
            "持股0檔的日數": int((res["npos"][a:b + 1] == 0).sum())}


def _ctrl(args):
    kind, r = args
    B = _G["book"]; L, k, pk = _G["cell"]
    rng = np.random.default_rng(SEED0 + r)
    if kind == "c":
        sel = {e: B.pick(e, L, k, "c", rng=rng) for e in B.reb}
    else:
        sel = {e: B.pick(e, L, k, pk, rng=rng, fake=True) for e in B.reb}
    res = sim_book(sel, _G["P"], _G["dl"], _G["t0"], _G["t1"], "hold")
    out = {"arm": kind, "r": r, "seed": SEED0 + r}
    for nm, (a, b) in _G["seg"].items():
        c, m, ratio = seg_metrics(res["eq"], a, b)
        out.update({f"{nm}_年化": c, f"{nm}_回落": m, f"{nm}_比值": ratio})
    return out


def selftest():
    """模擬器 fixture：手算值逐項比（容差 1e-12）。"""
    n = 40

    def mk(o, c=None, trd=None, up=None, dn=None):
        o = np.asarray(o, float); c = o.copy() if c is None else np.asarray(c, float)
        return {"o": o, "c": pd.Series(c).ffill().to_numpy(float), "trd": np.ones(n, bool) if trd is None else trd,
                "up_o": np.zeros(n, bool) if up is None else up, "dn_o": np.zeros(n, bool) if dn is None else dn, "dn_c": np.zeros(n, bool)}
    ok = []

    def chk(name, got, exp):
        good = abs(got - exp) < 1e-12; ok.append(good)
        print(f"  {'✅' if good else '❌'} {name}：得 {got!r}／應 {exp!r}")
    # F1 常數價：equity 只因成本變
    P = {"A": mk([10.0] * n), "B": mk([10.0] * n)}
    sel = {5: ["A", "B"], 15: ["A", "B"], 25: []}
    h = sim_book(sel, P, {}, 1, 35, "hold"); a_ = sim_book(sel, P, {}, 1, 35, "all")
    chk("F1 續抱：換股後不交易、最後全賣 ⇒ 1 − 0.2×COST", h["eq"][35], 1 - 0.2 * COST)
    chk("F1 續抱：t=14 equity ＝ 1（買進不扣）", h["eq"][14], 1.0)
    chk("F1 全賣全買：t=15 多付一次 0.2×COST", a_["eq"][15], 1 - 0.2 * COST)
    chk("F1 全賣全買：最後 1 − 0.4×COST（t=15 重買金額 ＝ equity[14]/10 ＝ 0.1）", a_["eq"][35], 1 - 0.4 * COST)
    chk("F1 成本差（續抱 − 全賣全買）＝ 0.2×COST", h["eq"][35] - a_["eq"][35], 0.2 * COST)
    # F2 已知報酬：A 在 t≥10 價變 20（開盤、收盤）
    pa = [10.0] * 10 + [20.0] * 30
    P = {"A": mk(pa), "B": mk([10.0] * n)}
    h = sim_book({5: ["A", "B"], 25: ["B"]}, P, {}, 1, 35, "hold")
    chk("F2 t=12：A 翻倍 ⇒ 1.1", h["eq"][12], 1.1)
    chk("F2 t=25 開盤賣 A（20）⇒ 1.1 − 0.1×COST", h["eq"][25], 1.1 - 0.1 * COST)
    chk("F2 t=25 續抱 B、持股 1 檔", float(h["npos"][25]), 1.0)
    # F3 漲停擋買、⛔ 不遞補：名單 [A, C]、只有 1 槽；A 開盤漲停 ⇒ 持現金、C 不遞補
    up = np.zeros(n, bool); up[5] = True
    P = {"A": mk([10.0] * n, up=up), "C": mk([10.0] * n)}
    h = sim_book({5: ["A", "C"]}, P, {}, 1, 10, "hold", n_slots=1)
    chk("F3 漲停擋買、1 槽 ⇒ 0 檔、C 不遞補", float(h["npos"][6]), 0.0)
    chk("F3 計數 limit_up", float(h["cnt"]["buy_blocked_limit_up"]), 1.0)
    # F4 跌停延後賣：A t=25 開盤跌停 ⇒ t=26 開盤賣（價 5）
    dn = np.zeros(n, bool); dn[25] = True
    pa = [10.0] * 25 + [5.0] * 15
    P = {"A": mk(pa, dn=dn)}
    h = sim_book({5: ["A"], 25: []}, P, {}, 1, 35, "hold")
    chk("F4 t=25 跌停賣不掉、照收盤計值 ⇒ 1 − 0.05", h["eq"][25], 0.95)
    chk("F4 t=26 開盤 5 賣出 ⇒ 0.95 − 0.1×COST", h["eq"][26], 0.95 - 0.1 * COST)
    # F5 下市：B 在 t=20 之後沒成交（官方下市）⇒ t=25 以最後收盤 8 了結
    trd = np.ones(n, bool); trd[21:] = False
    pb = [10.0] * 20 + [8.0] + [np.nan] * 19
    P = {"B": mk(pb, c=pb, trd=trd)}
    h = sim_book({5: ["B"], 25: []}, P, {"B": {"last": 20, "status": "delisted_official"}}, 1, 35, "hold")
    chk("F5 下市以最後收盤了結 ⇒ 1 − 0.02 − 0.1×COST", h["eq"][30], 1 - 0.02 - 0.1 * COST)
    chk("F5 計數 delist_settled", float(h["cnt"]["delist_settled"]), 1.0)
    h = sim_book({5: ["B"], 25: []}, P, {"B": {"last": 20, "status": "ambig"}}, 1, 35, "hold")
    chk("F5' ambig ⇒ 照停牌、不了結（持股 1）", float(h["npos"][35]), 1.0)
    # F6 金額 ＝ 前一日 equity ÷ 10（續抱不再平衡）：A 翻倍後 t=15 新買 C ⇒ C 金額 ＝ 1.1/10
    pa = [10.0] * 10 + [20.0] * 30
    P = {"A": mk(pa), "C": mk([10.0] * n)}
    h = sim_book({5: ["A"], 15: ["A", "C"]}, P, {}, 1, 20, "hold")
    chk("F6 equity ＝ 1.1（C 平盤）", h["eq"][20], 1.1)
    chk("F6 現金 ＝ 1 − 0.1 − 0.11（C 的金額 ＝ equity[14]/10、A 不再平衡）", h["cashf"][20] * h["eq"][20], 1 - 0.1 - 0.11)
    allok = all(ok)
    print(f"selftest {'全過' if allok else '⛔ 有不過'}（{sum(ok)}／{len(ok)}）")
    return allok, sum(ok), len(ok)


def main_body():
    t00 = time.time()
    procs = int(sys.argv[sys.argv.index("--procs") + 1]) if "--procs" in sys.argv else 2
    os.makedirs(OUT, exist_ok=True)
    LOG = open(os.path.join(OUT, "body.log"), "w", encoding="utf-8")

    def log(s):
        print(s, flush=True); LOG.write(s + "\n"); LOG.flush()
    stok, n_ok, n_all = selftest()
    if not stok:
        raise SystemExit("⛔ selftest 不過，停")
    log(f"[selftest] 模擬器 fixture {n_ok}／{n_all} 全過")
    cal = D.load_calendar(); n = len(cal)
    t0 = int(cal.searchsorted(pd.Timestamp(W0))); t1 = int(cal.searchsorted(pd.Timestamp(W1)))
    assert str(cal[t0].date()) == W0 and str(cal[t1].date()) == W1 and t1 - t0 + 1 == 2313
    SEGP = {}
    for nm, (a, b) in SEG.items():
        pa, pb = int(cal.searchsorted(pd.Timestamp(a))), int(cal.searchsorted(pd.Timestamp(b)))
        assert str(cal[pa].date()) == a and str(cal[pb].date()) == b, (nm, cal[pa], cal[pb])
        SEGP[nm] = (pa, pb)
    # ── U4 對帳
    cols = ["measure_date", "stock_id", "market", "eligible"]
    afc = pd.read_csv(PANEL_AFC, dtype={"stock_id": str}, usecols=cols, parse_dates=["measure_date"])
    ext = pd.read_csv(PANEL_EXT, dtype={"stock_id": str}, usecols=cols, parse_dates=["measure_date"])
    a_ = afc[afc["measure_date"] <= RECON_TO].sort_values(["measure_date", "stock_id"]).reset_index(drop=True)
    e_ = ext[ext["measure_date"] <= RECON_TO].sort_values(["measure_date", "stock_id"]).reset_index(drop=True)
    same = len(a_) == len(e_) and a_[["measure_date", "stock_id", "market"]].equals(e_[["measure_date", "stock_id", "market"]]) \
        and bool((a_["eligible"].astype(str).to_numpy() == e_["eligible"].astype(str).to_numpy()).all())
    recon = {"對帳範圍": f"量測日 ≤ {RECON_TO.date()}", "resultsAFC 列數": len(a_), "panel_ext 列數": len(e_),
             "resultsAFC eligible 真": int(a_["eligible"].astype(str).eq("True").sum()), "panel_ext eligible 真": int(e_["eligible"].astype(str).eq("True").sum()),
             "逐列相同（measure_date、stock_id、market、eligible）": bool(same),
             "resultsAFC 量測日": [str(afc["measure_date"].min().date()), str(afc["measure_date"].max().date())],
             "panel_ext 量測日": [str(ext["measure_date"].min().date()), str(ext["measure_date"].max().date())],
             "panel_ext 2026-03-02 之後的量測日": sorted(str(d.date()) for d in ext["measure_date"].unique() if d > RECON_TO)}
    json.dump(recon, open(os.path.join(OUT, "recon.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    log(f"[U4 對帳] {json.dumps(recon, ensure_ascii=False)}")
    if not same:
        raise SystemExit("⛔ panel_ext 與 resultsAFC 在 2026-03-02 以前不逐列相同 ⇒ 停下回報")
    # ── 資料
    stocks = pd.read_csv(os.path.join(H2.H2D, "meta", "stocks.csv"), dtype=str)
    G = UG.gate3(stocks)
    ind = pd.read_csv(os.path.join(H2.H2D, "meta", "industry.csv"), dtype=str)
    # ⚠ 查核抓到（2026-09-27）：industry.csv 有 40 列 industry_name 空白、只有代碼 ⇒ 32＝文化創意業（上櫃 26）、33＝農業科技（上櫃 4）、
    #   91＝存託憑證（上市 10）。pre 段的 dict 把這 40 檔併成同一個 NaN「類股」（⛔ 不是 U5 定案的「照原名」）⇒ 本體依代碼補名稱。
    blank = ind["industry_name"].isna() | (ind["industry_name"].astype(str).str.strip() == "")
    unk = sorted(set(ind.loc[blank, "industry_code"]) - set(CODE_NAME))
    if unk:
        raise SystemExit(f"⛔ industry.csv 有空白名稱、代碼不認得：{unk}")
    ind.loc[blank, "industry_name"] = ind.loc[blank, "industry_code"].map(CODE_NAME)
    n_blank = {c: int((ind.loc[blank, "industry_code"] == c).sum()) for c in CODE_NAME}
    ind = ind[ind["industry_name"] != "存託憑證"]
    cls = {s: NAME_MAP.get(nm, nm) for s, nm in zip(ind["stock_id"], ind["industry_name"])}
    assert all(isinstance(v, str) and v for v in cls.values())
    rev, _, _ = R34.load_revenue()
    rf = P4F.rev_hi24_flags(rev, cal)
    rd = R34.rebalance_dates(list(rev.index), cal, 10)
    reb = sorted({e for _, e in rd.values() if t0 <= e <= t1})
    with Pool(procs, initializer=_init, initargs=(cal,)) as pool:
        P = dict(pool.map(load_full, list(zip(G["stock_id"], G["market"])), chunksize=16))
    P = {s: v for s, v in P.items() if v is not None}
    dl = TR.delist_status({s: {"trd": v["trd"]} for s, v in P.items()}, cal, official=TR.load_official())
    log(f"[產業別] 名稱空白依代碼補 {n_blank}｜類股 {len(set(cls.values()))} 個（去存託憑證、上市櫃對齊後）")
    log(f"[資料] 快照 {H2.SHA[:10]}｜gate3 {len(G):,}｜有價 {len(P):,}｜有類股 {sum(s in cls for s in P):,}｜換股日 {len(reb)} 個（{cal[reb[0]].date()}～{cal[reb[-1]].date()}）"
        f"｜delist 狀態 {dict(Counter(v['status'] for v in dl.values()))}｜{time.time() - t00:.0f}s")
    pm = {d: g for d, g in ext.groupby("measure_date")}
    meas = sorted(pm)
    elig = {}; cov = []
    for e in reb:
        d = cal[e]; mm = [m for m in meas if m.year == d.year and m.month == d.month]
        if not mm:
            raise SystemExit(f"⛔ 換股日 {d.date()} 同月沒有量測日")
        g = pm[max(mm)]; el = [s for s in g.loc[g["eligible"].astype(str) == "True", "stock_id"] if s in P]
        elig[e] = el
        cov.append({"換股日": str(d.date()), "量測日": str(max(mm).date()), "eligible": len(el), "無類股": sum(s not in cls for s in el),
                    "無類股且已下市": sum((s not in cls) and dl.get(s, {}).get("status", "").startswith("delisted") for s in el)})
    cov = pd.DataFrame(cov); cov.to_csv(os.path.join(OUT, "coverage.csv"), index=False)
    nocls_share = cov["無類股"].sum() / cov["eligible"].sum()
    log(f"[類股覆蓋] 換股日 {len(cov)}｜eligible 中位 {cov['eligible'].median():.0f}｜無類股 {cov['無類股'].sum():,}／{cov['eligible'].sum():,} 股-月 ＝ {nocls_share:.2%}"
        f"（其中已下市 {cov['無類股且已下市'].sum():,}）")
    revset = {}
    for e in reb:
        row = rf.iloc[e]
        revset[e] = set(row.index[row.to_numpy() == 100])
    B = Book(reb, cal, P, cls, elig, revset)
    first_reb = reb[0]
    reb_seg = {nm: [e for e in reb if a <= e <= b] for nm, (a, b) in SEGP.items()}
    log(f"[換股日] 探索段 {len(reb_seg['探索'])}｜確認段 {len(reb_seg['確認'])}｜全 {len(reb)}（首 {cal[first_reb].date()}、末 {cal[reb[-1]].date()}）")
    # ── 0050
    bench = pd.Series(D.load_stock("0050", "twse", cal).df["close"].to_numpy(float)).ffill().to_numpy(float)
    c_full, m_full = R13.window_stats(bench, 0, n, t0, t1 + 1)
    anchor_ok = repr(float(c_full)) == repr(0.24020209886370614) and repr(float(m_full)) == repr(-0.3395700527611012)
    Z = {nm: seg_metrics(bench, a, b) for nm, (a, b) in SEGP.items()}
    log(f"[0050] 主窗 {c_full:.4%}／{m_full:.4%}（對錨 P17 W0 逐位元 {'✅' if anchor_ok else '❌'}）｜" +
        "｜".join(f"{nm} {v[0]:.2%}／{v[1]:.2%}／{v[2]:.3f}" for nm, v in Z.items()))
    if not anchor_ok:
        raise SystemExit("⛔ 0050 主窗對錨不過")
    # ── 18 格 × (月換續抱、月換全賣全買、季換續抱、抱 60 日)
    ROWS = []; EQ = {}; PICKROWS = []; RES = {}
    for L in LS:
        for k in KS:
            for pk in PICKS:
                key = f"L{L}_k{k}_{pk}"
                sel = {e: B.pick(e, L, k, pk) for e in reb}
                for e in reb:
                    for i, s in enumerate(sel[e]):
                        PICKROWS.append({"格": key, "換股日": str(cal[e].date()), "名次": i + 1, "sid": s, "類股": cls[s]})
                for var in ("月換續抱", "月換全賣全買", "季換續抱", "抱60日"):
                    if var == "抱60日":
                        rows = []
                        for e in reb:
                            for i, s in enumerate(sel[e]):
                                x = min(e + 59, n - 1); o_e = P[s]["o"][e]
                                g_ = P[s]["c"][x] / o_e - 1.0 if np.isfinite(o_e) and o_e > 0 else 0.0
                                rows.append({"sid": s, "entry_pos": e, "xpos_H60": x, "g_H60": g_, "score": -float(i)})
                        sig = pd.DataFrame(rows); us = sorted(sig["sid"].unique())
                        sv = R.simulate_mtm(sig, "H60", N, np.random.default_rng(SEED0), {s: P[s]["c"] for s in us}, {s: P[s]["o"] for s in us}, n,
                                            return_equity=True, pick="score",
                                            tradable={s: {kk: P[s][kk] for kk in ("trd", "up_o", "dn_o", "dn_c")} for s in us},
                                            delist={s: dl[s] for s in us if s in dl})
                        eq = np.array(sv["equity"], float); eq[:t0] = 1.0
                        extra = {k_: sv[k_] for k_ in sv if k_.startswith("tr_")}
                        for nm, (a, b) in SEGP.items():
                            c, m, ratio = seg_metrics(eq, a, b)
                            ROWS.append({"格": key, "L": L, "k": k, "挑法": pk, "版本": var, "段": nm, "年化": c, "回落": m, "比值": ratio,
                                         "槽使用率": float(sv["slot_use"]), "交易筆數": int(sv["trades"]), **{k_: float(v) for k_, v in extra.items()}})
                        EQ[f"{key}|{var}"] = eq
                        continue
                    if var == "季換續抱":
                        sl = {e: v for e, v in sel.items() if cal[e].month in (1, 4, 7, 10)}
                        mode = "hold"
                    else:
                        sl = sel; mode = "hold" if var == "月換續抱" else "all"
                    res = sim_book(sl, P, dl, t0, t1, mode, record=(var == "月換續抱"))
                    EQ[f"{key}|{var}"] = res["eq"]
                    if var == "月換續抱":
                        RES[key] = res
                    fr = min(sl)
                    for nm, (a, b) in SEGP.items():
                        rs = [e for e in reb_seg[nm] if e in sl]
                        st = cell_stats(res, (a, b), rs, cls, fr)
                        ROWS.append({"格": key, "L": L, "k": k, "挑法": pk, "版本": var, "段": nm, **st, **{f"cnt_{k_}": v for k_, v in res["cnt"].items()}})
                log(f"  {key} 完成｜{time.time() - t00:.0f}s")
    T = pd.DataFrame(ROWS); T.to_csv(os.path.join(OUT, "cells.csv"), index=False)
    pd.DataFrame(PICKROWS).to_csv(os.path.join(OUT, "picks.csv.gz"), index=False, compression={"method": "gzip", "mtime": 0})
    np.savez_compressed(os.path.join(OUT, "eq_cells.npz"), dates=np.array([str(d.date()) for d in cal[t0:t1 + 1]]),
                        **{k_.replace("|", "__"): v[t0:t1 + 1] for k_, v in EQ.items()})
    # ── 探索段挑格（月換續抱 18 格）
    ex = T[(T["版本"] == "月換續抱") & (T["段"] == "探索")].copy()
    c0, m0, r0 = Z["探索"]
    ex["過判準"] = (ex["年化"] > c0) & (ex["比值"] >= r0)
    pool_ = ex[ex["過判準"]] if ex["過判準"].any() else ex
    pool_ = pool_.assign(_pk=pool_["挑法"].map({"a": 0, "b": 1}))
    best = pool_.sort_values(["比值", "年化", "L", "k", "_pk"], ascending=[False, False, True, True, True]).iloc[0]
    ck = best["格"]; L, k, pk = int(best["L"]), int(best["k"]), best["挑法"]
    cf = T[(T["格"] == ck) & (T["版本"] == "月換續抱") & (T["段"] == "確認")].iloc[0]
    lab = label(cf["年化"], cf["回落"], Z["確認"][0], Z["確認"][1])
    log(f"[探索挑格] 過判準 {int(ex['過判準'].sum())}／18｜挑中 {ck}（探索 {best['年化']:.2%}／{best['回落']:.2%}／{best['比值']:.3f}）"
        f"｜確認 {cf['年化']:.2%}／{cf['回落']:.2%}／{cf['比值']:.3f} ⇒ 【{lab}】")
    # ── 對照：(c) 類股內隨機、假訊號臂（隨機 k 個類股）
    _G.update({"book": B, "cell": (L, k, pk), "P": P, "dl": dl, "t0": t0, "t1": t1, "seg": SEGP})
    tc = time.time()
    with Pool(procs) as pool:
        CT = pool.map(_ctrl, [("c", r) for r in range(REPS)] + [("fake", r) for r in range(REPS)], chunksize=10)
    CT = pd.DataFrame(CT); CT.to_csv(os.path.join(OUT, "controls.csv.gz"), index=False, compression={"method": "gzip", "mtime": 0})
    log(f"[對照] (c) 與假訊號臂各 {REPS} 次｜{time.time() - tc:.0f}s")
    # ── 營量 v1（#13）同段、持股重疊
    z13 = np.load("backtest/resultsYfMix13/eq_main.npz")
    assert int(z13["w0"]) == t0 and int(z13["w1"]) == t1
    b13 = np.ones(n); b13[t0:t1 + 1] = z13["b13"]; b13[t1 + 1:] = z13["b13"][-1]
    pos13 = pd.read_csv("backtest/resultsYfMix13/positions.csv.gz", dtype={"sid": str})
    pos13 = pos13[pos13["cell"] == 13]
    H13 = [set() for _ in range(n)]
    for s, tb, ts in zip(pos13["sid"], pos13["t_buy"], pos13["t_sell"]):
        ts = n if ts < 0 else ts
        for t in range(max(tb, t0), min(ts, t1 + 1)):
            H13[t].add(s)
    main = RES[ck]
    OV = {}
    for nm, (a, b) in SEGP.items():
        c13, m13, r13 = seg_metrics(b13, a, b)
        hd = [main["held_days"][t - t0] for t in range(a, b + 1)]
        ov_s = [len(h & H13[t]) / len(h) for h, t in zip(hd, range(a, b + 1)) if h]
        ov_13 = [len(h & H13[t]) / len(H13[t]) for h, t in zip(hd, range(a, b + 1)) if H13[t]]
        OV[nm] = {"營量v1_年化": c13, "營量v1_回落": m13, "營量v1_比值": r13, "重疊÷本格持股_逐日均值": float(np.mean(ov_s)),
                  "重疊÷營量v1持股_逐日均值": float(np.mean(ov_13)),
                  "同時持有檔數_逐日均值": float(np.mean([len(h & H13[t]) for h, t in zip(hd, range(a, b + 1))])),
                  "營量v1持股數_逐日均值": float(np.mean([len(H13[t]) for t in range(a, b + 1)]))}
    # ── 挑中格：各年報酬、最常入選類股前 5
    yrs = {}; byr = {}
    for y in range(cal[t0].year, cal[t1].year + 1):
        idx = [t for t in range(t0, t1 + 1) if cal[t].year == y]
        tag = str(y) + ("（03-02 起）" if y == cal[t0].year else "（至 08-24）" if y == cal[t1].year else "")
        for nm_, arr, dd in (("本格", main["eq"], yrs), ("0050", bench, byr)):
            base = arr[idx[0] - 1] if idx[0] > t0 else arr[t0]
            dd[tag] = float(arr[idx[-1]] / base - 1)
    topc = {}
    for nm in SEGP:
        cc = Counter(cls[s] for e in reb_seg[nm] for s in main["hold"][e])
        tot = sum(cc.values())
        topc[nm] = [(c_, v, v / tot) for c_, v in cc.most_common(5)]
    top1 = Counter(B.M[(e, L)][2][0] for e in reb)
    # ── 對照彙總
    SUM = {}
    for nm in SEGP:
        real = float(T[(T["格"] == ck) & (T["版本"] == "月換續抱") & (T["段"] == nm)]["年化"].iloc[0])
        for arm in ("c", "fake"):
            x = CT[CT["arm"] == arm][f"{nm}_年化"].to_numpy(float)
            SUM[f"{arm}_{nm}"] = {"本格年化": real, "中位": float(np.median(x)), "p10": float(np.quantile(x, 0.1)), "p90": float(np.quantile(x, 0.9)),
                                  "p（年化 ≥ 本格的比例）": float(np.mean(x >= real)), "本格贏過的比例": float(np.mean(x < real)),
                                  "贏0050同段的比例": float(np.mean(x > Z[nm][0])), "回落中位": float(np.median(CT[CT["arm"] == arm][f"{nm}_回落"]))}
    pfake = SUM["fake_確認"]["p（年化 ≥ 本格的比例）"]
    OUTJ = {"性質": "PREREG強勢類股 本體（12 處未列預設照暫定 (i) 全部定案）", "快照": H2.SHA, "U4 對帳": recon,
            "0050": {nm: dict(zip(("年化", "回落", "比值"), v)) for nm, v in Z.items()}, "0050主窗對錨": anchor_ok,
            "類股覆蓋": {"換股日": len(cov), "eligible中位": float(cov["eligible"].median()), "無類股占eligible股月": float(nocls_share),
                     "無類股股月": int(cov["無類股"].sum()), "eligible股月": int(cov["eligible"].sum()), "無類股且已下市股月": int(cov["無類股且已下市"].sum())},
            "換股日數": {nm: len(v) for nm, v in reb_seg.items()},
            "產業別": {"名稱空白依代碼補": n_blank, "類股數": len(set(cls.values())),
                    "每月可排名類股數中位": {f"L{L_}": float(np.median([len(B.M[(e, L_)][2]) for e in reb])) for L_ in LS}},
            "探索挑格": {"過判準格數": int(ex["過判準"].sum()), "挑中": ck, "L": L, "k": k, "挑法": pk,
                     "探索": {"年化": float(best["年化"]), "回落": float(best["回落"]), "比值": float(best["比值"])}},
            "確認": {"年化": float(cf["年化"]), "回落": float(cf["回落"]), "比值": float(cf["比值"]), "判定": lab},
            "假訊號p_確認": pfake, "對照": SUM, "營量v1": OV, "挑中格各年": yrs, "0050各年": byr, "挑中格類股前5": topc,
            "類股強度第一名次數（挑中格的 L）": dict(top1.most_common(8)), "挑中格計數": main["cnt"], "selftest": f"{n_ok}/{n_all}"}
    json.dump(OUTJ, open(os.path.join(OUT, "body.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    log(f"[對照] (c) 確認中位 {SUM['c_確認']['中位']:.2%}｜假訊號 確認中位 {SUM['fake_確認']['中位']:.2%}、p ＝ {pfake:.3f}｜營量v1 確認 {OV['確認']['營量v1_年化']:.2%}")
    log(f"本體完成 {time.time() - t00:.0f}s")


if __name__ == "__main__":
    {"pre": main_pre, "selftest": selftest, "body": main_body}[sys.argv[1] if len(sys.argv) > 1 else "pre"]()

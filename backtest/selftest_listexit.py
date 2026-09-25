# -*- coding: utf-8 -*-
"""PREREG名單出場 乙（裁定線 seq189；台股策略線登錄 seq1 sha db11230f58632a0d）：引擎三參數（stop_line_le、stop_proceeds、stop_block；
stop_line＋trim gain 同開）與停損線建構器（backtest/listexit_lines.py）的 fixture 與閘門。回測線，2026-09-26。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 python backtest/selftest_listexit.py fixtures  # ATR 手算、S2 兩讀法手算、S1 等號、停損待買、組合格順序、
                                                                                      # 停損擋賣、隨機獨立重建、無前視、突變體、防呆、None 路徑
    ... gate1   # 回歸閘 1：regress_tradability(18)＋regress_delist(6)＋改前（blob 52ce7677＝b1717d5c19）／改後 A/B（真資料，42 種組合 × 2 種子）
    ... gate2   # 回歸閘 2：selftest_avgengine3.py all（內含 avgengine2 all ⇒ avgengine all、P9 全套、P9 基準臂、avgdown F1～F10）
    ... t1gate  # #1 t−1 H120 用 listexit_lines 包裝、不開任何新參數重跑 20 顆 ⇒ 與 resultsN17/regime_t1/seeds.csv t1 #1 逐位元相同；
                #   另查證：rerun17 的 opens 在停牌日是不是 NaN（stop_block 描述版的差別在哪）
    ... nonid   # 6 格（＋S2 above_ep、兩個擋賣描述版）各 5 顆：只報觸發次數、待買筆數、等待天數、現金比例均值、待買部位占權益中位、
                #   停損後 20 個交易日內又買回同檔次數；⛔ 不報年化、回落（⛔ 不跑 200 顆）
    ... all

⭐ 改前引擎從 git 物件庫取（ORIG_BLOB）；LX_ENGINE_SRC／LX_LINES_SRC ⇒ 換檔前測暫存檔。
⚠ gate2 會改寫 resultsAvg/engine_b_*／b2_*／b3_*.json 與 resultsp9_engine/ 的入庫檔 ⇒ 跑前存位元組、跑完逐檔寫回。
結果寫到 backtest/resultsListExit/engine_{fixtures,gate1,gate2,t1gate,nonid}.json。
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import time
from collections import deque

import numpy as np
import pandas as pd

REPO = os.path.expanduser("~/tw-p17")
sys.path.insert(0, REPO)
OUT = os.path.join(REPO, "backtest", "resultsListExit")
PY = sys.executable
ORIG_BLOB = "52ce7677bced465cc7a0ce2ab03b9be84f9420b4"      # 改動前 HEAD:backtest/research11.py（b1717d5c19＝nx_cap 交件）
T1 = {"trim_rule": {"kind": "gain", "x": 0.15, "frac": 0.5}}
RESULTS: list = []
EXTRA: dict = {}

from backtest import selftest_p9engine as SP9        # noqa: E402  ⭐ 只借小工具
px, run, same_out, trad_of, close_to, fin, NC = SP9.px, SP9.run, SP9.same_out, SP9.trad_of, SP9.close_to, SP9.fin, SP9.NC


def chk(name, cond, detail=""):
    RESULTS.append({"name": name, "ok": bool(cond), "detail": detail})
    print(("  ✓ " if cond else "  ✗ ") + name + (f"｜{detail}" if detail else ""), flush=True)
    return bool(cond)


def dump(tag):
    os.makedirs(OUT, exist_ok=True)
    p = os.path.join(OUT, f"engine_{tag}.json")
    d = {"when": pd.Timestamp.now(tz="Asia/Taipei").strftime("%Y-%m-%d %H:%M"), "n": len(RESULTS),
         "fail": sum(not r["ok"] for r in RESULTS), "checks": RESULTS}
    if EXTRA:
        d["extra"] = EXTRA
    json.dump(d, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    print(f"寫入 {p}：{len(RESULTS)} 條，失敗 {d['fail']}")


# ─────────────────────────── 引擎與建構器（新／改前／突變體）
def _src(env, mod):
    p = os.environ.get(env)
    if p:
        return open(p, encoding="utf-8").read(), p
    m = __import__(f"backtest.{mod}", fromlist=["x"])
    return open(m.__file__, encoding="utf-8").read(), m.__file__


def engine_new():
    s, f = _src("LX_ENGINE_SRC", "research11")
    if os.environ.get("LX_ENGINE_SRC"):
        return SP9._load_src(s, "backtest._r11_lx_new", f)
    from backtest import research11 as R
    return R


def lines_new():
    s, f = _src("LX_LINES_SRC", "listexit_lines")
    if os.environ.get("LX_LINES_SRC"):
        return SP9._load_src(s, "backtest._lxl_new", f)
    from backtest import listexit_lines as L
    return L


def engine_orig():
    src = subprocess.check_output(["git", "-C", REPO, "cat-file", "-p", ORIG_BLOB]).decode("utf-8")
    return SP9._load_src(src, "backtest._r11_orig_lx", os.path.join(REPO, "backtest", "research11.py"))


ENG_MUT = {
    "ML_le": ("(c <= lv[i] if stop_line_le else c < lv[i])", "c < lv[i]"),                           # 等號選項沒作用
    "ML_nxstop": ("if _nx_stop and sid in hit_now:", "if False:"),                                   # 停損的錢不進待買
    "ML_block": ('can = bool(stop_block[sid]["trd"][t]) and not bool(stop_block[sid]["dn_o"][t])', "can = True"),   # 擋賣沒作用
    "ML_pend": ("if stop_line is not None and sid in sl_pending:", "if False:"),                     # 停損待賣中照樣賣半
    "ML_lag": ("c = float(closes[sid][t - 1])  # _SLLAG", "c = float(closes[sid][t])  # _SLLAG"),   # 停損改讀當天收盤（前視）
    "MN_after": ("_nx_buy = not (len(open_pos) < ns_t and min(slot, _nx_gen) > 1e-9)   # _NXAFTER_WHO", "_nx_buy = True   # _NXAFTER_WHO"),  # D1 沒作用
    "MN_gen": ("amt = min(slot, cash if _nx_gen is None else _nx_gen)   # _NXAFTER_GEN", "amt = min(slot, cash)   # _NXAFTER_GEN"),       # 一般部位動到待買的錢
}
LIN_MUT = {
    "MB_hs": ('hi = -np.inf if high_start == "entry_close" else ep', 'hi = ep if high_start == "entry_close" else -np.inf'),   # 兩讀法對調
    "MB_ge": ("if cj > hi:", "if cj >= hi:"),                                                       # 平高點也算新高
    "MB_down": ("cur = max(cur, cj - mult * float(atr[j]))", "cur = cj - mult * float(atr[j])"),     # 線可以下降
    "MB_atr0": ("a0 = float(atr[k])", "a0 = float(atr[k + 1])"),                                     # 起始用進場日 ATR
    "MB_fut": ("cj = float(c_cal[d])", "cj = float(c_cal[min(d + 1, len(c_cal) - 1)])"),             # 讀到明天收盤（前視）
}


def mut_of(kind, tag):
    if kind == "eng":
        s, f = _src("LX_ENGINE_SRC", "research11"); a, b = ENG_MUT[tag]
    else:
        s, f = _src("LX_LINES_SRC", "listexit_lines"); a, b = LIN_MUT[tag]
    if s.count(a) != 1:
        raise SystemExit(f"⛔ 突變點 {tag} 找不到或不唯一：{a!r}")
    return SP9._load_src(s.replace(a, b), f"backtest._lx_{tag}", f)


def strip(o):
    return {k: v for k, v in o.items() if k != "_audit"}


def wilder_ind(h, l, c, n=14, min_bars=114):
    """獨立寫法（純迴圈）：TR ＝ max(h−l, |h−c前|, |l−c前|)（第 0 根 h−l）；第 n−1 根 ＝ 前 n 個 TR 平均；之後 (前×(n−1)＋TR)/n；前 min_bars−1 根 NaN。"""
    m = len(c); tr = [0.0] * m; out = [float("nan")] * m
    for i in range(m):
        tr[i] = h[i] - l[i] if i == 0 else max(h[i] - l[i], abs(h[i] - c[i - 1]), abs(l[i] - c[i - 1]))
    if m < n:
        return np.array(out)
    a = sum(tr[:n]) / n; out[n - 1] = a
    for i in range(n, m):
        a = (a * (n - 1) + tr[i]) / n; out[i] = a
    for i in range(min(min_bars - 1, m)):
        out[i] = float("nan")
    return np.array(out)


def wilder_plain(h, l, c, n=14):
    """隨機小世界用（NC＝100 不夠 114 根）：同 Wilder、⛔ 不設前 113 根 NaN；只讀 ≤ i 的資料。"""
    return wilder_ind(h, l, c, n, min_bars=1)


def early_exits(o, rows):
    """audit ⇒ 停損出場（賣出日 ＜ 該訊號列的排程出場日）與買進。回 (stops [(t, sid)], buys [(t, sid, kind)])。"""
    xmap = {(s, e): x for s, e, x in rows}
    pos = {}; stops = []; buys = []
    for r in o["_audit"]:
        if r["side"] == "buy":
            pos[r["sid"]] = int(r["t"]); buys.append((int(r["t"]), r["sid"], r.get("kind")))
        elif "kind" not in r:
            e = pos.pop(r["sid"])
            if int(r["t"]) < xmap[(r["sid"], e)]:
                stops.append((int(r["t"]), r["sid"]))
    return stops, buys


# ─────────────────────────── 手算小例（每條回 (名, ok, 細節)；同一組拿去跑突變體）
def fx_list(R, L):
    C = R.COST
    out = []

    def add(nm, ok, det=""):
        out.append((nm, bool(ok), det))

    def safe(fn):
        try:
            fn()
        except Exception as e:  # noqa: BLE001
            out.append((fn.__name__, False, f"例外 {type(e).__name__}: {e}"))

    def a_atr():
        m = 130
        c = np.full(m, 10.0); h = np.full(m, 10.5); l = np.full(m, 9.5)
        h[120] = 12.0                                  # TR ＝ max(2.5, 2, 0.5) ＝ 2.5
        c[124] = 8.0; h[125] = 10.2; l[125] = 9.9     # TR(125) ＝ max(0.3, |10.2−8|, |9.9−8|) ＝ 2.2（用前一根收盤）
        a = R.wilder_atr(h, l, c)
        a120 = (1.0 * 13 + 2.5) / 14; a121 = (a120 * 13 + 1.0) / 14
        ok = np.isnan(a[112]) and close_to(a[113], 1.0) and close_to(a[119], 1.0) and close_to(a[120], a120) and close_to(a[121], a121)
        tr124 = max(1.0, abs(10.5 - 10.0), abs(9.5 - 10.0)); tr125 = 2.2
        exp = a121
        for i in range(122, 126):
            tr = {124: max(10.5 - 9.5, abs(10.5 - 10.0), abs(9.5 - 10.0)), 125: tr125}.get(i, 1.0)
            exp = (exp * 13 + tr) / 14
        ok = ok and close_to(a[125], exp)
        add("A1 ATR 手算（Wilder n＝14）：TR 恆 1 ⇒ ATR[113]＝1（前 113 根 NaN）；h 跳到 12 ⇒ ATR[120]＝(13＋2.5)/14；"
            "前一根收盤 8 ⇒ TR[125]＝2.2（用前收盤、真實高低價）", ok, f"ATR[120] {a[120]!r} vs {a120!r}；ATR[125] {a[125]!r} vs {exp!r}；tr124 {tr124}")
        rng = np.random.default_rng(5); bad = 0
        for w in range(50):
            m = int(rng.integers(120, 400)); c = 50 * np.exp(np.cumsum(rng.normal(0, 0.02, m)))
            h = c * (1 + rng.random(m) * 0.03); l = c * (1 - rng.random(m) * 0.03)
            x, y = R.wilder_atr(h, l, c), wilder_ind(h, l, c)
            bad += not (np.array_equal(np.isnan(x), np.isnan(y)) and np.allclose(x[~np.isnan(x)], y[~np.isnan(y)], rtol=0, atol=1e-12))
        add("A2 ATR 對獨立寫法（純迴圈）：隨機 50 條逐點相同（容差 1e-12）", bad == 0, f"不符 {bad}")

    def b_s2():
        # ep＝10、ATR(訊號日 k＝4)＝0.5 ⇒ 起始 9.0；ATR(5)＝ATR(6)＝ATR(8)＝0.1、其餘 0.5
        idx = np.arange(20); atr = np.full(20, 0.5); atr[[5, 6, 8]] = 0.1
        c = np.full(20, 10.0); c[5] = 9.9; c[6] = 9.6; c[7] = 10.4; c[8] = 10.4; c[9] = 11.0
        s, lv = L.trail_levels(idx, atr, c, 4, 10.0, 15, 2.0, "entry_close")
        want = [9.9 - 0.2, 9.7, 9.7, 9.7, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0]
        add("B1 S2 entry_close 手算：起始 9.0；d5 收盤 9.9 是第一個高點 ⇒ 9.9−0.2＝9.7；d7 10.4 新高但 10.4−1.0＜9.7 ⇒ 不降；"
            "d8 平高點 10.4 ⇒ 不算新高；d9 11.0 ⇒ 10.0", s == 5 and np.allclose(lv, want, atol=1e-12), f"{np.round(lv, 6).tolist()}")
        s, lv = L.trail_levels(idx, atr, c, 4, 10.0, 15, 2.0, "above_ep")
        want = [9.0, 9.0, 9.4, 9.4, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0]
        add("B2 S2 above_ep 手算：d5 9.9、d6 9.6 都沒超過進場價 10 ⇒ 維持 9.0；d7 10.4 ⇒ 9.4；d8 平高點不算；d9 11.0 ⇒ 10.0",
            np.allclose(lv, want, atol=1e-12), f"{np.round(lv, 6).tolist()}")
        # 兩讀法進引擎：d6 收盤 9.6 ＜ 9.7 ⇒ entry_close 在 t＝7 開盤出；above_ep 不出（9.6 ≥ 9.0）
        o_ = np.full(NC, 10.0); cc = np.full(NC, 10.0); cc[5] = 9.9; cc[6] = 9.6; cc[7] = 10.4; cc[8] = 10.4; cc[9] = 11.0; o_[7] = 9.5
        ex = {}
        for hs in L.HIGH_STARTS:
            st, lv = L.trail_levels(np.arange(NC), np.r_[atr, np.full(NC - 20, 0.5)], cc, 4, 10.0, 60, 2.0, hs)
            o = run(R, [("A", 5, 60)], {"A": (o_, cc)}, 2, stop_line={("A", 5): (st, lv)})
            ex[hs] = [(r["t"], r["px"]) for r in o["_audit"] if r["side"] == "sell"]
        add("B3 兩讀法進引擎：entry_close ⇒ t＝7 開盤 9.5 出；above_ep ⇒ 抱到排程出場 t＝60", ex["entry_close"][:1] == [(7, 9.5)] and ex["above_ep"][:1] == [(60, 10.0)],
            f"{ex}")
        # 非有效 K 棒（停牌）：idx 跳過 12、13 ⇒ 線沿用 11 的；ffill 收盤不算新高
        idx2 = np.r_[np.arange(12), np.arange(14, 30)]; atr2 = np.full(len(idx2), 0.5)
        c2 = np.full(40, 10.0); c2[11] = 11.0; c2[12] = 11.0; c2[13] = 11.0; c2[14] = 11.5
        s, lv = L.trail_levels(idx2, atr2, c2, 4, 10.0, 16, 2.0, "entry_close")
        want = [9.0] * 6 + [10.0, 10.0, 10.0, 10.5, 10.5, 10.5]      # d5..d10 起始／平；d11 11.0 ⇒ 10.0；d12、13 停牌沿用；d14 11.5 ⇒ 10.5
        add("B4 只數有效 K 棒：停牌日（12、13）線沿用前一根、ffill 收盤不當新高；d14 復牌 11.5 ⇒ 10.5", np.allclose(lv, want, atol=1e-12), f"{np.round(lv, 6).tolist()}")
        st1 = L.trail_levels(idx, np.r_[np.nan, atr[1:]] * 0 + np.nan, c, 4, 10.0, 15)
        add("B5 ATR(訊號日) 無效 ⇒ 不建線（回 None）", st1 is None)

    def c_s1():
        # S1 等號：ep 10、線 9.0；收盤[20]＝9.0 ⇒ stop_line_le 在 t＝21 開盤 8.8 出；預設（嚴格 ＜）不出
        pr = {"A": px((0, 20, 10, 10), (20, 21, 10, 9.0), (21, NC, 8.8, 9.0))}
        sl = {("A", 10): (10, np.full(51, 0.9 * 10.0))}
        o = run(R, [("A", 10, 60)], pr, 2, stop_line=sl, stop_line_le=True)
        o0 = run(R, [("A", 10, 60)], pr, 2, stop_line=sl)
        g = 8.8 / 10.0 - 1.0
        add("C1 S1「收盤 ≤ ep×0.90」：收盤恰 9.0 ⇒ stop_line_le 在次日（t＝21）開盤 8.8 整檔出、期末 0.5＋0.5×(1＋g−COST)；預設嚴格 ＜ ⇒ 抱到 60",
            [(r["t"], r["px"]) for r in o["_audit"] if r["side"] == "sell"] == [(21, 8.8)] and close_to(fin(o), 0.5 + 0.5 * (1 + g - C))
            and [r["t"] for r in o0["_audit"] if r["side"] == "sell"] == [60] and o["sl_exits"] == 1,
            f"期末 {fin(o):.12f}")
        pr2 = {"A": px((0, 20, 10, 10), (20, NC, 10, 9.01))}
        o = run(R, [("A", 10, 60)], pr2, 2, stop_line=sl, stop_line_le=True)
        add("C2 收盤 9.01 ＞ 9.0 ⇒ 不出", o["sl_exits"] == 0)
        # s1_lines 的 ep 照引擎規則：進場日開盤 NaN ⇒ 用收盤
        oA = np.full(NC, 10.0); oA[10] = np.nan; cA = np.full(NC, 10.0); cA[10] = 12.0
        sig = pd.DataFrame({"sid": ["A"], "entry_pos": [10], "xpos_HX": [60], "g_HX": [0.0]})
        lines = L.s1_lines(sig, "HX", {"A": oA}, {"A": cA})
        au = []
        R.simulate_mtm(sig, "HX", 2, np.random.default_rng(0), {"A": cA}, {"A": oA}, NC, return_equity=True, audit=au,
                       stop_line=lines, stop_line_le=True)
        epx = [r["px"] for r in au if r["side"] == "buy"][0]
        add("C3 s1_lines 的 ep ＝ 引擎進場價（開盤 NaN ⇒ 收盤 12）⇒ 線 ＝ 0.9×12 ＝ 10.8", close_to(lines[("A", 10)][1][0], 0.9 * 12.0) and close_to(epx, 12.0),
            f"線 {lines[('A', 10)][1][0]!r}、引擎 ep {epx!r}")

    def d_nx():
        # 停損的錢進待買：N＝2；A 在 t＝21 開盤 8.8 停損；t＝30 量測日 C ⇒ 用 A 的淨入帳全額買（等 9 天）
        pr = {"A": px((0, 20, 10, 10), (20, 21, 10, 8.9), (21, NC, 8.8, 8.8)), "B": px(), "C": px()}
        sl = {("A", 10): (10, np.full(51, 9.0)), ("B", 10): (10, np.full(61, 9.0)), ("C", 30): (30, np.full(51, 9.0))}
        rows = [("A", 10, 60), ("B", 10, 70), ("C", 30, 80)]
        o = run(R, rows, pr, 2, stop_line=sl, stop_line_le=True, stop_proceeds="next")
        g = 8.8 / 10.0 - 1.0; L1 = 0.5 * (1 + g - C)
        nb = [(r["t"], r["sid"], r["amt"]) for r in o["_audit"] if r.get("kind") == "nx"]
        add("D1 停損全出的淨入帳 0.5×(1＋g−COST) ⇒ 一筆待買 ⇒ t＝30 C 全額買（waits [9]、x_nx_stop_lots 1）",
            len(nb) == 1 and nb[0][:2] == (30, "C") and repr(float(nb[0][2])) == repr(float(L1)) and o["x_nx_waits"] == [9] and o["x_nx_stop_lots"] == 1,
            f"{nb}；L1 {L1!r}")
        oo = run(R, rows, pr, 2, stop_line=sl, stop_line_le=True)
        c30 = [(r["sid"], r.get("kind"), round(r["amt"], 9)) for r in oo["_audit"] if r["side"] == "buy" and r["t"] == 30]
        add("D2 描述 ⓐ 閒置版（stop_proceeds 不開）：t＝30 C 照一般新部位 min(slot, 現金) 買、沒有 kind nx、沒有 x_nx 鍵",
            len(c30) == 1 and c30[0][1] is None and "x_nx_n" not in oo, f"{c30}")
        # 同日：停損在 t＝30 開盤、t＝30 本身是量測日 ⇒ 當天用停損的錢買（槽也是當天空出來的）
        pr2 = {"A": px((0, 29, 10, 10), (29, 30, 10, 8.9), (30, NC, 8.8, 8.8)), "B": px(), "C": px()}
        sl2 = {("A", 10): (10, np.full(51, 9.0)), ("B", 10): (10, np.full(61, 9.0)), ("C", 30): (30, np.full(51, 9.0))}
        o = run(R, rows, pr2, 2, stop_line=sl2, stop_line_le=True, stop_proceeds="next")
        seq = [(r["side"], r["sid"], r.get("kind")) for r in o["_audit"] if r["t"] == 30]
        add("D3 同日（登錄「次一交易日的訊號池」＝ 賣出那天）：t＝30 開盤停損 A、同日 C 用待買買進（waits [0]）、總數仍 2",
            seq == [("sell", "A", None), ("buy", "C", "nx")] and o["x_nx_waits"] == [0], f"{seq}")

    def e_combo():
        # S1＋T1：A 收盤[20] 11.6 ⇒ t＝21 開盤 11.8 賣半（待買 L1）；收盤[40] 8.9 ⇒ t＝41 開盤 8.8 停損剩下一半（待買 L2）
        #   N＝3、B 持有；t＝45 量測日 D、E ⇒ 兩筆都買（先 L1 後 L2）
        pr = {"A": px((0, 20, 10, 10), (20, 21, 10, 11.6), (21, 40, 11.8, 11.8), (40, 41, 11.8, 8.9), (41, NC, 8.8, 8.8)),
              "B": px(), "D": px(), "E": px()}
        rows = [("A", 10, 60), ("B", 10, 70), ("D", 45, 90), ("E", 45, 90)]
        sl = {(s, e): (e, np.full(x - e + 1, 9.0)) for s, e, x in rows}
        o = run(R, rows, pr, 3, stop_line=sl, stop_line_le=True, stop_proceeds="next", trim_proceeds="next", **T1)
        a = 1 / 3
        L1 = a * 0.5 * 11.8 / 10.0 - a * 0.5 * C
        L2 = (a * 0.5) * (1 + (8.8 / 10.0 - 1.0)) - (a * 0.5) * C
        nb = [(r["t"], round(r["amt"], 12)) for r in o["_audit"] if r.get("kind") == "nx"]
        add("E1 S1＋T1：先賣半（L1＝a×0.5×11.8/10 − a×0.5×COST）、後停損剩下一半（L2＝剩名目×(1＋g) − 剩成本×COST）⇒ t＝45 先 L1 後 L2",
            nb == [(45, round(L1, 12)), (45, round(L2, 12))] and (o["x_trim_n"], o["sl_exits"], o["x_nx_stop_lots"]) == (1, 1, 1),
            f"{nb}；L1 {L1:.12f}、L2 {L2:.12f}")
        # 同日先停損再賣半：t＝22 兩條都觸發（收盤[21] 同時 ≤ 9.0 不可能 ⇒ 用 S2 那種高線造）⇒ 停損整檔出、⛔ 不賣半
        pr2 = {"A": px((0, 21, 10, 10), (21, 22, 10, 11.6), (22, NC, 11.8, 11.8)), "B": px()}
        lvA = np.zeros(51); lvA[21 - 10:] = 12.0                 # 線在 d＝21 才升到 12（之前 0）
        sl2 = {("A", 10): (10, lvA), ("B", 10): (10, np.full(61, 0.0))}
        o = run(R, [("A", 10, 60), ("B", 10, 70)], pr2, 3, stop_line=sl2, **T1)
        add("E2 同日先處理停損：收盤[21] 11.6 同時觸發停利（≥ 11.5）與停損（＜ 12）⇒ t＝22 整檔停損、⛔ 不賣半",
            not [r for r in o["_audit"] if r.get("kind") == "trim"] and [r["t"] for r in o["_audit"] if r["side"] == "sell" and r["sid"] == "A"] == [22])
        # 停損待賣中不賣半：stop_block 擋 t＝21、22；收盤[21] 11.6（合成大跳）⇒ t＝22 停利條件成立但停損待賣 ⇒ 不賣半；t＝23 整檔出
        pr3 = {"A": px((0, 20, 10, 10), (20, 21, 10, 8.9), (21, 22, 9.0, 11.6), (22, NC, 11.8, 11.8)), "B": px()}
        blk = trad_of(pr3, dn=[("A", 21), ("A", 22)])
        sl3 = {("A", 10): (10, np.full(51, 9.0)), ("B", 10): (10, np.full(61, 0.0))}
        o = run(R, [("A", 10, 60), ("B", 10, 70)], pr3, 3, stop_line=sl3, stop_line_le=True, stop_block=blk, **T1)
        sells = [(r["t"], r.get("kind")) for r in o["_audit"] if r["side"] == "sell" and r["sid"] == "A"]
        add("E3 停損已觸發、開盤跌停賣不掉（stop_block）期間 ⇒ ⛔ 不賣半；第一個可賣開盤（t＝23）整檔出", sells == [(23, None)], f"{sells}")

    def f_block():
        pr = {"A": px((0, 20, 10, 10), (20, 21, 10, 8.9), (21, NC, 8.8, 8.8)), "B": px(), "C": px()}
        rows = [("A", 10, 60), ("B", 10, 40), ("C", 30, 80)]
        sl = {("A", 10): (10, np.full(51, 9.0)), ("B", 10): (10, np.full(31, 0.0)), ("C", 30): (30, np.full(51, 0.0))}
        blk = trad_of(pr, dn=[("A", 21), ("B", 40)], halt=[("A", 22), ("C", 30)])
        o = run(R, rows, pr, 3, stop_line=sl, stop_line_le=True, stop_block=blk)
        sA = [r["t"] for r in o["_audit"] if r["side"] == "sell" and r["sid"] == "A"]
        sB = [r["t"] for r in o["_audit"] if r["side"] == "sell" and r["sid"] == "B"]
        bC = [r["t"] for r in o["_audit"] if r["side"] == "buy" and r["sid"] == "C"]
        add("F1 stop_block：停損 t＝21 開盤跌停、t＝22 停牌 ⇒ t＝23 開盤出（sl_block_days 2）；只擋停損：B 排程出場日跌停照出、C 進場日停牌照買",
            sA == [23] and sB == [40] and bC == [30] and o["sl_block_days"] == 2 and o["sl_delayed_days"] == 2, f"A {sA}、B {sB}、C {bC}")
        o0 = run(R, rows, pr, 3, stop_line=sl, stop_line_le=True)
        add("F2 同例不開 stop_block ⇒ t＝21 開盤出（跌停也假設賣得掉，＝ #1 原樣）", [r["t"] for r in o0["_audit"] if r["side"] == "sell" and r["sid"] == "A"] == [21])

    def g_d1():
        # D1 一般新部位優先（nx_order="after"）
        pr = {"A": px((0, 20, 10, 10), (20, 21, 10, 11.6), (21, NC, 11.8, 11.8)), "B": px(), "D": px()}
        rows = [("A", 10, 60), ("B", 10, 70), ("D", 30, 80)]
        ob = run(R, rows, pr, 3, trim_proceeds="next", **T1)
        oa = run(R, rows, pr, 3, trim_proceeds="next", nx_order="after", **T1)
        kb = [(r["sid"], r.get("kind")) for r in ob["_audit"] if r["side"] == "buy" and r["t"] == 30]
        ka = [(r["sid"], r.get("kind"), r["amt"]) for r in oa["_audit"] if r["side"] == "buy" and r["t"] == 30]
        gen = 1.0 - 1 / 3 - 1 / 3
        add("G1 D1（N＝3、空槽 1、待買 1）：before ⇒ 待買買 D；after ⇒ D 用一般現金 min(slot, 現金 − 待買)＝1−2/3 買、待買留著（期末未買 1）",
            kb == [("D", "nx")] and [k[:2] for k in ka] == [("D", None)] and close_to(ka[0][2], gen) and oa["x_nx_pending_end"] == 1 and ob["x_nx_n"] == 1,
            f"before {kb}；after {[(s, k, round(a, 9)) for s, k, a in ka]}")
        # N＝5：A 賣半（待買 L）、B 漲到 5 倍 ⇒ slot 大；t＝30 候選 4、空槽 3 ⇒ after：一般 slot、一般（剩下的一般現金）、第三檔才給待買
        pr2 = {"A": px((0, 20, 10, 10), (20, 21, 10, 11.6), (21, NC, 11.8, 11.8)), "B": px((0, 24, 10, 10), (24, NC, 50, 50)),
               **{s: px() for s in "DEFG"}}
        rows2 = [("A", 10, 60), ("B", 10, 70)] + [(s, 30, 80) for s in "DEFG"]
        ob = run(R, rows2, pr2, 5, trim_proceeds="next", **T1)
        oa = run(R, rows2, pr2, 5, trim_proceeds="next", nx_order="after", **T1)
        kb = [r.get("kind") for r in ob["_audit"] if r["side"] == "buy" and r["t"] == 30]
        ba = [(r.get("kind"), r["amt"]) for r in oa["_audit"] if r["side"] == "buy" and r["t"] == 30]
        L = 0.2 * 0.5 * 11.8 / 10.0 - 0.2 * 0.5 * C
        slot = float(oa["equity"][29]) / 5
        g0 = (1.0 - 0.2 - 0.2)
        ok = kb == ["nx", "nx", None] and [k for k, _ in ba] == [None, None, "nx"] and oa["x_nx_pending_end"] == 1 and close_to(ba[0][1], slot) and close_to(ba[1][1], g0 - slot) \
            and close_to(ba[2][1], L)
        add("G2 D1（N＝5、空槽 3；A、B 都賣半 ⇒ 待買 2 筆）：before ⇒ [待買, 待買, 一般]；after ⇒ [一般 slot, 一般（一般現金用完）, 待買 A 全額 L]、"
            "B 那筆留著；一般部位合計 ＝ 一般現金 0.6、⛔ 沒動到待買",
            ok, f"before {kb}；after {[(k, round(a, 9)) for k, a in ba]}；slot {slot:.9f}")

    def h_d2():
        # D2（併池）＝ trim_proceeds=None：S1＋T1 只開 stop_proceeds ⇒ 賣半的錢併入一般現金（不成待買）、停損的錢成待買
        pr = {"A": px((0, 20, 10, 10), (20, 21, 10, 11.6), (21, 40, 11.8, 11.8), (40, 41, 11.8, 8.9), (41, NC, 8.8, 8.8)),
              "B": px(), "D": px(), "E": px()}
        rows = [("A", 10, 60), ("B", 10, 70), ("D", 45, 90), ("E", 45, 90)]
        sl = {(s, e): (e, np.full(x - e + 1, 9.0)) for s, e, x in rows}
        o = run(R, rows, pr, 3, stop_line=sl, stop_line_le=True, stop_proceeds="next", **T1)
        a = 1 / 3; L2 = (a * 0.5) * (1 + (8.8 / 10.0 - 1.0)) - (a * 0.5) * C
        nb = [(r["t"], round(r["amt"], 12)) for r in o["_audit"] if r.get("kind") == "nx"]
        add("H1 D2 併池（S1＋T1、trim_proceeds 不開）：賣半的錢併入一般現金、只有停損那筆成待買（x_nx_stop_lots 1、待買 [L2]）",
            (o["x_trim_n"], o["x_nx_stop_lots"]) == (1, 1) and nb[:1] == [(45, round(L2, 12))] and len(nb) == 1, f"{nb}")

    for fn in (a_atr, b_s2, c_s1, d_nx, e_combo, f_block, g_d1, h_d2):
        safe(fn)
    return out


def world(rng, n_sid=5, trad=False):
    sids = [f"S{i}" for i in range(n_sid)]
    pr = {}
    for s in sids:
        c = 10 * np.exp(np.cumsum(rng.normal(0.0, 0.04, NC)))
        o = np.r_[10.0, c[:-1]] * np.exp(rng.normal(0, 0.01, NC))
        pr[s] = (o, c)
    rows = []
    for d in range(5, 80, 5):
        for s in rng.choice(sids, int(rng.integers(0, 4)), replace=False):
            rows.append((str(s), d, min(NC - 1, d + int(rng.integers(10, 45)))))
    return pr, rows, int(rng.integers(2, 5)), (dict(tradable=trad_of(pr)) if trad else {})


def lines_for(L, pr, rows, kind):
    """S1：0.9×ep 常數；S2：trail_levels（ATR ＝ wilder_plain，因果）。"""
    opens = {s: p[0] for s, p in pr.items()}; closes = {s: p[1] for s, p in pr.items()}
    sig = pd.DataFrame([{"sid": s, "entry_pos": e, "xpos_HX": x} for s, e, x in rows])
    if kind == "S1":
        return L.s1_lines(sig, "HX", opens, closes)
    out = {}
    for s, e, x in rows:
        o, c = pr[s]
        h, l = np.maximum(o, c) * 1.01, np.minimum(o, c) * 0.99
        r = L.trail_levels(np.arange(NC), wilder_plain(h, l, c), c, e - 1, L.engine_ep(opens, closes, s, e), x)
        if r is not None:
            out[(s, e)] = r
    return out


def replay_lx(o, rows, N, lines, le):
    """獨立重建：停損時點（第一個 t−1 ≥ 進場、收盤 ≤／＜ 線 ⇒ t 開盤出，排程出場前）、待買（賣半＋停損）先進先出全額、
    每個量測日待買數 ＝ min(空槽, 候選, 待買)、不重複買、持有 ≤ N、計數鍵。"""
    ent = {}
    for s, e, x in rows:
        ent.setdefault(e, []).append(s)
    xmap = {(s, e): x for s, e, x in rows}
    by_t = {}
    for r in o["_audit"]:
        by_t.setdefault(int(r["t"]), []).append(r)
    held = {}; lots = deque(); waits = []; st = {"stop": 0, "nx": 0}
    for t in sorted(set(by_t) | set(ent)):
        rt = by_t.get(t, []); i = 0
        while i < len(rt) and rt[i]["side"] == "sell":
            r = rt[i]; s = r["sid"]
            if r.get("kind") == "trim":
                lots.append((r["amt"] - r["cost"], t))
            else:
                e = held.pop(s)
                x = xmap[(s, e)]
                c = o["_closes"][s]
                if (s, e) in lines:
                    st0, lv = lines[(s, e)]
                    trig = [u for u in range(e, x - 1) if (c[u] <= lv[u - st0] if le else c[u] < lv[u - st0])]
                else:
                    trig = []                                   # 沒建線（ATR(訊號日) 無效）⇒ 不停損
                exp_t = trig[0] + 1 if trig else x
                if t != exp_t:
                    return False, f"t={t} {s} 出場日應 {exp_t}", st
                if t < x:
                    lots.append((r["amt"] - r["cost"], t)); st["stop"] += 1
            i += 1
        bs = rt[i:]
        if any(r["side"] != "buy" for r in bs):
            return False, f"t={t} 同日順序錯", st
        if t in ent:
            cand = [s for s in ent[t] if s not in held]
            free = N - len(held)
            want = min(free, len(cand), len(lots)) if free > 0 else 0
            kinds = [r.get("kind") for r in bs]
            if kinds.count("nx") != want or kinds != sorted(kinds, key=lambda k: 0 if k == "nx" else 1):
                return False, f"t={t} 待買 {kinds}，應 {want} 筆在前", st
        elif bs:
            return False, f"t={t} 非量測日買進", st
        for r in bs:
            if r["sid"] in held:
                return False, f"t={t} 買已持有", st
            if r.get("kind") == "nx":
                a, ts = lots.popleft()
                if not close_to(float(r["amt"]), float(a), 1e-12):
                    return False, f"t={t} 待買金額 {r['amt']!r} ≠ {a!r}", st
                waits.append(t - ts); st["nx"] += 1
            held[r["sid"]] = t
        if len(held) > N:
            return False, f"t={t} 持有 ＞ N", st
    got = (o["x_nx_n"], o["x_nx_waits"], o["x_nx_pending_end"], o["x_nx_stop_lots"], o["sl_exits"])
    exp = (st["nx"], waits, len(lots), st["stop"], st["stop"])
    return (got == exp), ("" if got == exp else f"引擎 {got} ≠ 重建 {exp}"), st


def rand_lx(R, L, n_w=300, seed=20260929):
    rng = np.random.default_rng(seed); n_ok = 0; bad = []; agg = {"停損": 0, "待買": 0, "有停損的世界": 0}
    for w in range(n_w):
        pr, rows, N, _ = world(rng)
        if not rows:
            n_ok += 1; continue
        kind = "S1" if w % 2 else "S2"; le = kind == "S1"
        try:
            lines = lines_for(L, pr, rows, kind)
            kw = dict(stop_line=lines, stop_line_le=le, stop_proceeds="next")
            if w % 3:
                kw.update(trim_proceeds="next", **T1)
            o = run(R, rows, pr, N, seed=w, **kw)
            o["_closes"] = {s: p[1] for s, p in pr.items()}
            ok, why, st = replay_lx(o, rows, N, lines, le)
        except Exception as e:  # noqa: BLE001
            ok, why, st = False, f"例外 {type(e).__name__}: {e}", {}
        n_ok += ok
        if not ok:
            bad.append((w, why)); continue
        agg["停損"] += st["stop"]; agg["待買"] += st["nx"]; agg["有停損的世界"] += st["stop"] > 0
    return n_ok, n_w, agg, bad


def lookahead_lx(R, L, n_w=200, seed=20260930):
    """整條管線（建線＋引擎）無前視：改 t＝s 的收盤與 s＋1 起的開收盤 ⇒ 線在 ≤ s 不變、t ≤ s 的交易與 equity[:s] 不變。"""
    rng = np.random.default_rng(seed); n_ok = n_post = 0
    for w in range(n_w):
        pa, rows, N, _ = world(rng)
        if not rows:
            n_ok += 1; continue
        exits = {x for _, _, x in rows}
        s = int(rng.integers(15, 75))
        while s in exits:
            s += 1
        pb = {}
        for i, sd in enumerate(pa):
            o, c = pa[sd][0].copy(), pa[sd][1].copy()
            f = (0.7 if (w + i) % 2 else 1.35) * np.exp(np.cumsum(rng.normal(0, 0.02, NC - s)))
            c[s:] = c[s:] * f; o[s + 1:] = o[s + 1:] * f[:-1]
            pb[sd] = (o, c)
        kind = "S1" if w % 2 else "S2"
        try:
            outs = []
            for P in (pa, pb):
                lines = lines_for(L, P, rows, kind)
                kw = dict(stop_line=lines, stop_line_le=kind == "S1", stop_proceeds="next", trim_proceeds="next", **T1)
                if w % 4 >= 2:
                    kw["nx_order"] = "after"
                outs.append(run(R, rows, P, N, seed=w, **kw))
            oa, ob = outs
            ta = [r for r in oa["_audit"] if r["t"] <= s]; tb = [r for r in ob["_audit"] if r["t"] <= s]
            n_ok += repr(ta) == repr(tb) and oa["equity"][:s].tobytes() == ob["equity"][:s].tobytes()
            n_post += repr(oa["_audit"]) != repr(ob["_audit"])
        except Exception:  # noqa: BLE001
            pass
    return n_ok, n_post, n_w


def fixtures():
    R = engine_new(); L = lines_new()
    print(f"── 引擎 {os.environ.get('LX_ENGINE_SRC') or R.__file__}｜建構器 {os.environ.get('LX_LINES_SRC') or L.__file__}")
    import inspect
    p_ = inspect.signature(R.simulate_mtm).parameters
    chk("三個新參數存在、預設關閉（stop_line_le=False、stop_proceeds=None、stop_block=None）",
        p_["stop_line_le"].default is False and p_["stop_proceeds"].default is None and p_["stop_block"].default is None)
    FX = fx_list(R, L)
    for nm, ok, det in FX:
        chk(nm, ok, det)
    print("── 隨機獨立重建（S1／S2 線 × 停損待買 × 一部分開 T1＋賣半待買）")
    n_ok, n_w, agg, bad = rand_lx(R, L)
    chk(f"隨機 {n_w} 個世界：停損時點、待買（停損＋賣半）先進先出全額、每個量測日待買數、不重複買、持有 ≤ N、計數鍵 全部與獨立重建相符",
        n_ok == n_w and agg["有停損的世界"] >= 50, f"{n_ok}/{n_w}；{json.dumps(agg, ensure_ascii=False)}；{bad[:2]}")
    n_ok, n_post, n_w = lookahead_lx(R, L)
    chk(f"無前視（建線＋引擎整條，隨機 {n_w} 個世界）：t ≤ s 的交易與 equity[:s] 全部不變、之後確實不同 ≥ 一半", n_ok == n_w and n_post >= n_w // 2,
        f"{n_ok}/{n_w}；後段不同 {n_post}")
    print("── 鑑別力（突變體）")
    mut = {}
    for kind, tags in (("eng", ENG_MUT), ("lin", LIN_MUT)):
        for tag in tags:
            M = mut_of(kind, tag)
            RR_, LL_ = (M, L) if kind == "eng" else (R, M)
            failed = [nm.split("：")[0].split(" ")[0] for nm, ok, _ in fx_list(RR_, LL_) if not ok]
            if tag in ("ML_lag", "MB_fut"):
                a, _, b = lookahead_lx(RR_, LL_, n_w=100)
                mut[tag] = {"fixture 沒過": failed, "無前視抓到": f"{b - a}/{b}"}
                chk(f"鑑別力 {tag}（前視）", b - a > 0, json.dumps(mut[tag], ensure_ascii=False))
            else:
                a, b, _, _ = rand_lx(RR_, LL_, n_w=100)
                mut[tag] = {"fixture 沒過": failed, "隨機重建抓到": f"{b - a}/{b}"}
                chk(f"鑑別力 {tag}", bool(failed) or a < b, json.dumps(mut[tag], ensure_ascii=False))
    EXTRA["突變體"] = mut
    print("── None 路徑：新參數全省略／明寫預設 ⇒ 與改前引擎（b1717d5c19）逐位元同")
    R0 = engine_orig()
    rng = np.random.default_rng(12); n_same = n_all = 0; why_ = []
    for w in range(60):
        pr, rows, N, extra = world(rng, trad=bool(w % 3 == 0))
        if not rows:
            continue
        lines = lines_for(L, pr, rows, "S2")
        for kw0 in (dict(), dict(stop_line=lines), dict(trim_proceeds="next", **T1), dict(trim_proceeds="next", nx_cap=N + 2, **T1),
                    dict(add_rule={"kind": "loss", "x": 0.10})):
            for kw1 in (dict(kw0), dict(kw0, stop_line_le=False, stop_proceeds=None, stop_block=None, nx_order="before")):
                a0 = run(R0, rows, pr, N, seed=w, **kw0, **extra); a1 = run(R, rows, pr, N, seed=w, **kw1, **extra)
                ok, why = same_out(strip(a0), strip(a1)); ok = ok and repr(a0["_audit"]) == repr(a1["_audit"])
                n_all += 1; n_same += ok
                if not ok:
                    why_.append((w, why))
    chk("新參數省略／明寫預設 ×（全關、stop_line、T1＋待買、T1＋待買＋nx_cap、乙一 loss）× 隨機世界（1/3 開 tradable）⇒ 與改前引擎逐位元同",
        n_same == n_all, f"{n_same}/{n_all}；{why_[:2]}")
    print("── 防呆")
    rows = [("A", 10, 60)]; pr = {"A": px()}; sl = {("A", 10): (10, np.full(51, 9.0))}
    for nm, kw in (("stop_line_le 沒開 stop_line", dict(stop_line_le=True)), ("stop_line_le＝1（非布林）", dict(stop_line=sl, stop_line_le=1)),
                   ("stop_proceeds 沒開 stop_line", dict(stop_proceeds="next")), ("stop_proceeds＝'idle'", dict(stop_line=sl, stop_proceeds="idle")),
                   ("stop_block 沒開 stop_line", dict(stop_block=trad_of(pr))),
                   ("stop_line＋trim 2-C ⓐ（loss）", dict(stop_line=sl, trim_rule={"x": 0.10, "frac": 0.5})),
                   ("stop_line＋add_rule", dict(stop_line=sl, add_rule={"kind": "loss", "x": 0.10})),
                   ("stop（fix）＋trim gain", dict(stop=("fix", 0.10), **T1)),
                   ("nx_order＝'later'", dict(trim_proceeds="next", nx_order="later", **T1)),
                   ("nx_order＝'after' 沒開待買", dict(nx_order="after", **T1))):
        try:
            run(R, rows, pr, 2, **kw); ok = False
        except ValueError:
            ok = True
        chk(f"防呆：{nm} ⇒ ValueError", ok)
    try:
        run(R, rows, pr, 2, stop_line=sl, stop_proceeds="next", nx_cap=3); ok = True
    except ValueError:
        ok = False
    chk("stop_proceeds 可配 nx_cap（不報錯）", ok)


# ─────────────────────────── 回歸閘 1
def gate1():
    os.chdir(REPO)
    if not os.environ.get("LX_ENGINE_SRC"):
        for scr, n in (("regress_tradability.py", 18), ("regress_delist.py", 6)):
            p = subprocess.run([PY, os.path.join(REPO, "backtest", scr), "check"], cwd=REPO, capture_output=True, text=True)
            tail = [ln for ln in p.stdout.strip().split("\n") if ln][-1:] if p.stdout else []
            chk(f"{scr} check（{n} 組）逐位元相同", p.returncode == 0 and "✅" in p.stdout, " ".join(tail) + (p.stderr[-300:] if p.returncode else ""))
    print("── 回歸閘 1-b：改前（blob 52ce7677）／改後 A/B（真資料、門檻B、H120、N=8、種子 0,1）")
    from backtest import tradability as T
    R = engine_new(); R0 = engine_orig()
    cal, ncal, uni, panel, closes, opens, sig, bench = SP9.load_real()
    trad = T.build(set(sig["sid"]), cal); dl = T.delist_status(trad, cal, official=T.load_official())
    wk = np.zeros(ncal, bool); wk[1:] = R.regime_below(bench, 60)[:-1]
    caps = np.full(ncal, 8, int); caps[1500:1700] = 5
    sl = {(r.sid, int(r.entry_pos)): (int(r.entry_pos), np.full(130, float(opens[r.sid][int(r.entry_pos)]) * 0.85)) for r in sig.itertuples()}
    hi = {s: (pd.Series(c).rolling(120).max().to_numpy() <= c) for s, c in ((s, np.asarray(closes[s], float)) for s in set(sig["sid"]))}
    G_ = {"kind": "gain", "x": 0.15, "frac": 0.5}
    CFG = {"plain": {}, "stop_fix": dict(stop=("fix", 0.10)), "stop_trail": dict(stop=("trail", 0.15)), "log": dict(_log=True),
           "queue": dict(d_max=2, queue_days=3, _log=True), "bench": dict(cash_mode="bench", bench=bench),
           "weak_maxw": dict(weak=wk, weak_size=0.5, report_maxw=True, maxw_detail=True),
           "weight_fn": dict(weight_fn=lambda batch, t, eq, cash: [eq / 8 * (1.0 + 0.1 * (i % 2)) for i in range(len(batch))]),
           "caps": dict(n_slots=caps), "cap_fn": dict(cap_fn=lambda sid, t, hs: not (str(sid).startswith("2") and len(hs) >= 4), _log=True),
           "pick": dict(pick="relvol"), "tradable": dict(tradable=trad), "tradable_delist": dict(tradable=trad, delist=dl, _audit=True, _log=True),
           "stop_line": dict(stop_line=sl, tradable=trad),
           "P9 2-A k=2＋audit": dict(entry_tranches=2, _audit=True), "P9 2-A k=3": dict(entry_tranches=3),
           "P9 2-B ⓐ gain＋audit": dict(add_rule={"kind": "gain", "x": 0.15}, _audit=True),
           "P9 2-B ⓐ gain partial": dict(add_rule={"kind": "gain", "x": 0.15, "short": "partial"}),
           "P9 2-B ⓑ flag": dict(add_rule={"kind": "flag", "flags": hi}), "P9 2-B ⓒ hold": dict(add_rule={"kind": "hold", "days": 40}),
           "P9 2-C ⓐ trim＋audit": dict(trim_rule={"x": 0.10, "frac": 0.5}, _audit=True),
           "P9 2-C ⓐ trim（kind='loss' 明寫）": dict(trim_rule={"kind": "loss", "x": 0.10, "frac": 0.5}),
           "P9 2-C ⓐ trim＋tradable＋delist＋audit＋log": dict(trim_rule={"x": 0.10, "frac": 0.5}, tradable=trad, delist=dl, _audit=True, _log=True),
           "P9 2-B ⓐ gain＋tradable＋delist＋audit": dict(add_rule={"kind": "gain", "x": 0.15}, tradable=trad, delist=dl, _audit=True),
           "P9 2-C ⓒ mult 1.5 MA60": dict(size_mult_by_regime={"mult": 1.5, "ma": 60, "bench": bench}),
           "P9 2-C ⓓ mult 0.5 MA20": dict(size_mult_by_regime={"mult": 0.5, "ma": 20, "bench": bench}),
           "P9 2-C ⓕ regime_trim MA60＋audit": dict(regime_trim={"hold": 0.5, "ma": 60, "bench": bench}, _audit=True),
           "P9 2-C ⓗ regime_trim MA10＋tradable": dict(regime_trim={"hold": 0.5, "ma": 10, "bench": bench}, tradable=trad),
           "乙一 add loss＋audit": dict(add_rule={"kind": "loss", "x": 0.10, "size": 0.5, "short": "skip"}, _audit=True),
           "乙一 add loss partial＋tradable＋delist": dict(add_rule={"kind": "loss", "x": 0.10, "short": "partial"}, tradable=trad, delist=dl),
           "乙二 trim gain＋audit（閒置版）": dict(trim_rule=G_, _audit=True),
           "乙二 trim gain＋tradable＋delist＋audit＋log": dict(trim_rule=G_, tradable=trad, delist=dl, _audit=True, _log=True),
           "乙二 next＋audit": dict(trim_rule=G_, trim_proceeds="next", _audit=True),
           "乙二 next＋log": dict(trim_rule=G_, trim_proceeds="next", _log=True),
           "乙二 next＋tradable＋delist＋audit＋log": dict(trim_rule=G_, trim_proceeds="next", tradable=trad, delist=dl, _audit=True, _log=True),
           "乙二 next＋caps＋audit": dict(trim_rule=G_, trim_proceeds="next", n_slots=caps, _audit=True),
           "乙二 next＋pick＋queue＋log": dict(trim_rule=G_, trim_proceeds="next", pick="relvol", d_max=2, queue_days=3, _log=True),
           "乙二 next＋nx_cap=10＋audit": dict(trim_rule=G_, trim_proceeds="next", nx_cap=10, _audit=True),
           "乙二 next＋nx_cap=10＋caps＋log": dict(trim_rule=G_, trim_proceeds="next", nx_cap=10, n_slots=caps, _log=True),
           "stop_line（無 tradable）＋audit＋log": dict(stop_line=sl, _audit=True, _log=True),
           "stop_line＋tradable＋delist＋audit": dict(stop_line=sl, tradable=trad, delist=dl, _audit=True),
           "stop_line（改後明寫 stop_line_le=False、stop_proceeds=None、stop_block=None）＋audit": dict(stop_line=sl, _audit=True, _none=True)}
    n_ok = n_all = 0; bad = []
    for name, cfg in CFG.items():
        for seed in (0, 1):
            outs = []
            for eng in (R0, R):
                kw = dict(cfg); lg = [] if kw.pop("_log", False) else None; au = [] if kw.pop("_audit", False) else None
                if kw.pop("_none", False) and eng is R:
                    kw.update(stop_line_le=False, stop_proceeds=None, stop_block=None)
                N = kw.pop("n_slots", 8)
                o = eng.simulate_mtm(sig, "H120", N, np.random.default_rng(seed), closes, opens, ncal, return_equity=True, log=lg, audit=au, **kw)
                outs.append((o, repr(lg), repr(au)))
            ok, why = same_out(outs[0][0], outs[1][0])
            ok = ok and outs[0][1] == outs[1][1] and outs[0][2] == outs[1][2]
            n_all += 1; n_ok += ok
            if not ok:
                bad.append((name, seed, why))
        print(f"  {name} {'✗' if any(b[0] == name for b in bad) else '✓'}", flush=True)
    chk(f"A/B 矩陣：{len(CFG)} 種既有參數組合 × 2 種子 ＝ {n_all} 組，改前（b1717d5c19）／改後逐位元相同（equity bytes、全部回傳鍵、log、audit）",
        n_ok == n_all, f"{n_ok}/{n_all}；{bad[:3]}")
    EXTRA["A/B 組合"] = list(CFG)


# ─────────────────────────── 回歸閘 2
def _snap(d, pred=lambda f: True):
    return {f: open(os.path.join(d, f), "rb").read() for f in os.listdir(d) if os.path.isfile(os.path.join(d, f)) and pred(f)}


def gate2():
    os.chdir(REPO)
    d9 = os.path.join(REPO, "backtest", "resultsp9_engine"); dA = os.path.join(REPO, "backtest", "resultsAvg")
    isb = lambda f: f.startswith(("engine_b_", "engine_b2_", "engine_b3_"))      # noqa: E731
    s9 = _snap(d9); sA = _snap(dA, isb); sA_all = set(os.listdir(dA))
    print(f"── 回歸閘 2（先存 resultsp9_engine/ {len(s9)} 個檔、resultsAvg/engine_b*_ {len(sA)} 個檔，跑完寫回）")
    env = {k: v for k, v in os.environ.items() if not k.startswith(("AVG_ENGINE", "LX_"))}
    js = {}
    try:
        t0 = time.time()
        p = subprocess.run([PY, os.path.join(REPO, "backtest", "selftest_avgengine3.py"), "all"], cwd=REPO, capture_output=True, text=True, env=env)
        got = {"rc": p.returncode, "secs": round(time.time() - t0), "err": p.stderr[-2000:] if p.returncode else ""}
        print(f"  [selftest_avgengine3.py all] rc={p.returncode}（{got['secs']}s）", flush=True)
        for tag in ("fixtures", "gate1", "gate2", "nonid"):
            js[tag] = json.loads(open(os.path.join(dA, f"engine_b3_{tag}.json"), encoding="utf-8").read())
    finally:
        for d, snap, pred in ((d9, s9, lambda f: True), (dA, sA, isb)):
            for f in list(os.listdir(d)):
                pth = os.path.join(d, f)
                if os.path.isfile(pth) and pred(f) and f not in snap:
                    os.remove(pth)
            for f, b in snap.items():
                open(os.path.join(d, f), "wb").write(b)
        back = all(open(os.path.join(d9, f), "rb").read() == b for f, b in s9.items()) and \
            all(open(os.path.join(dA, f), "rb").read() == b for f, b in sA.items())
        new_files = sorted(set(os.listdir(dA)) - sA_all) + sorted(set(os.listdir(d9)) - set(s9))
        print(f"  已寫回原位元組：{back}；多出來的檔 {new_files}")
    chk("selftest_avgengine3.py all 結束碼 0", got["rc"] == 0, got["err"][-300:])
    for tag, want_n in (("fixtures", 27), ("gate1", 3), ("gate2", 15), ("nonid", 3)):
        d = js[tag]
        chk(f"selftest_avgengine3 {tag}：{d['n'] - d['fail']}/{d['n']} 過（b1717d5c19 交件時 {want_n} 條全過）", d["fail"] == 0 and d["n"] == want_n,
            "; ".join(c["name"][:60] for c in d["checks"] if not c["ok"])[:500])
    g2 = js["gate2"]["checks"]
    for key in ("selftest_avgengine2", "（內含）selftest_avgengine", "（內含）（內含）selftest_p9engine", "（內含）（內含）P9 基準臂",
                "（內含）（內含）selftest_p9_builders", "（內含）selftest_avgdown", "P9 基準臂"):
        hit = [c for c in g2 if c["name"].startswith(key)]
        chk(f"（內含）{key}（{len(hit)} 條）", len(hit) >= 1 and all(c["ok"] for c in hit), hit[0]["name"][:120] if hit else "找不到")
    chk("既有結果檔已逐位元組寫回（resultsp9_engine/、resultsAvg/engine_b_*／b2_*／b3_*）", back and not new_files, f"多出來的檔 {new_files}")
    EXTRA["avgengine3 逐支"] = {t: {"n": js[t]["n"], "fail": js[t]["fail"]} for t in js}
    EXTRA["子行程秒"] = got["secs"]


# ─────────────────────────── #1 t−1 逐位元閘＋停牌日開盤查證
def t1gate(reps=20):
    L = lines_new(); R = engine_new()
    ctx = L.setup_t1(lambda x: print("  " + x, flush=True))
    RR, D = ctx["RR"], ctx["D"]
    ref = pd.read_csv(os.path.join(RR.OUT, "regime_t1", "seeds.csv"), dtype={"eq_sha": str}, float_precision="round_trip")
    ref = ref[(ref["stage"] == "t1") & (ref["cell"] == 1)].set_index("r")
    bad = []
    for r in range(reps):
        o = L.sim(ctx, {}, r, eng=R)
        c, m, v = RR.win_metrics(o["equity"], o["first"], o["end"], ctx["w0"], ctx["w1"])
        row = {"first": int(o["first"]), "end": int(o["end"]), "trades": int(o["trades"]),
               "eq_sha": hashlib.sha256(np.asarray(o["equity"], float).tobytes()).hexdigest()[:16]}
        q = ref.loc[r]
        same = all(repr(float(x)) == repr(float(q[k])) for k, x in (("cagr", c), ("mdd", m), ("vol", v))) and \
            all(int(row[k]) == int(q[k]) for k in ("first", "end", "trades")) and row["eq_sha"] == str(q["eq_sha"])
        if not same:
            bad.append(r)
        del o, c, m, v                                    # ⛔ 不印、不存年化／回落
    chk(f"#1 t−1 H120（listexit_lines.sim、不開任何新參數）{reps} 顆 ⇒ 與 resultsN17/regime_t1/seeds.csv t1 #1 逐位元相同"
        "（cagr／mdd／vol 以 repr 比、first／end／trades、eq_sha；⛔ 數值不印）", not bad, f"不同 {bad}")
    sig = ctx["sig"]
    chk("訊號列：rows、sid 數、entry_pos 範圍（描述）", True, f"{len(sig):,} 列／{sig['sid'].nunique():,} 檔；entry_pos {int(sig['entry_pos'].min())}～{int(sig['entry_pos'].max())}")
    # 查證：rerun17 opens 在停牌日（df traded＝False）是不是 NaN
    n_halt = n_halt_nan = n_trd_nan = n_trd = 0
    for sid in sorted(set(sig["sid"])):
        st = D.load_stock(sid, ctx["mk"].get(sid, "twse"), ctx["cal"])
        trd = st.df["traded"].to_numpy(bool); op = np.asarray(ctx["opens"][sid], float)
        n_halt += int((~trd).sum()); n_halt_nan += int((~trd & ~np.isfinite(op)).sum())
        n_trd += int(trd.sum()); n_trd_nan += int((trd & ~(np.isfinite(op) & (op > 0))).sum())
    EXTRA["停牌日開盤查證"] = {"停牌日（traded＝False）": n_halt, "其中 opens 為 NaN": n_halt_nan, "有成交日": n_trd, "有成交日但 opens 無效": n_trd_nan}
    chk("查證：rerun17 的 opens 在停牌日（traded＝False）全是 NaN ⇒ 原版的停損在停牌日本來就賣不掉（延到下一個有效開盤）；"
        "描述版 stop_block 與原版的差別只在【開盤跌停】", n_halt == n_halt_nan and n_trd_nan == 0, json.dumps(EXTRA["停牌日開盤查證"], ensure_ascii=False))
    return ctx


# ─────────────────────────── nonid（⛔ 只報次數、等待、現金比例、待買占比、再買回）
def _nx_frac(o, closes, w0, w1):
    """audit 重建：待買買進的部位（kind nx）逐日市值 ÷ equity（窗內中位）。"""
    eq = np.asarray(o["equity"], float); val = np.zeros(len(eq)); cur = {}
    ev = sorted(((int(r["t"]), i, r) for i, r in enumerate(o["_audit"])), key=lambda z: (z[0], z[1]))
    segs = []
    for t, _, r in ev:
        s = r["sid"]
        if r["side"] == "buy":
            if r.get("kind") == "nx":
                cur[s] = [t, float(r["amt"]), float(r["px"])]
        elif s in cur:
            if r.get("kind") == "trim":
                a, b = cur[s][0], t
                segs.append((s, a, b, cur[s][1], cur[s][2])); cur[s] = [t, cur[s][1] * 0.5, cur[s][2]]
            elif "kind" not in r:
                a, b = cur[s][0], t
                segs.append((s, a, b, cur[s][1], cur[s][2])); del cur[s]
    for s, (a, n, ep) in cur.items():
        segs.append((s, a, len(eq), n, ep))
    for s, a, b, n, ep in segs:
        c = np.asarray(closes[s], float)
        val[a:b] += n * c[a:b] / ep
    f = val[w0:w1 + 1] / eq[w0:w1 + 1]
    return float(np.median(f))


def nonid(ctx=None, seeds=5):
    L = lines_new(); R = engine_new()
    if ctx is None:
        ctx = L.setup_t1(lambda x: print("  " + x, flush=True))
    from backtest import research11 as R11
    cal = ctx["cal"]; sig = ctx["sig"]; w0, w1 = ctx["w0"], ctx["w1"]
    t0 = time.time()
    S1 = L.s1_lines(sig, "H120", ctx["opens"], ctx["closes"])
    bars = lambda s: R11.load_bars(s, ctx["mk"].get(s, "twse"), cal)   # noqa: E731
    S2, sk = L.s2_lines(sig, "H120", ctx["opens"], ctx["closes"], bars, 2.0, "entry_close")
    from backtest import tradability as T
    blk = T.build(set(sig["sid"]), cal)
    EXTRA["建線"] = {"S1": len(S1), "S2（甲 entry_close）": len(S2), "S2 略過（ATR(訊號日) 無效或讀不到 K 棒）": sk,
                   "訊號日有效 K 棒 ＜ 114 根（k ＜ 113）的訊號列": int((sig["k"] < 113).sum()), "ATR": L.ATR_NOTE}
    print(f"  [建線] {EXTRA['建線']}｜{time.time() - t0:.0f}s", flush=True)
    NX = dict(trim_proceeds="next"); T2 = {"trim_rule": {"kind": "gain", "x": 0.30, "frac": 0.5}}
    s1 = dict(stop_line=S1, stop_line_le=True); s2 = dict(stop_line=S2); sp = dict(stop_proceeds="next")
    CELLS = {
        "S1": {**s1, **sp}, "S2": {**s2, **sp}, "T1": {**T1, **NX}, "T2": {**T2, **NX},
        "S1＋T1": {**s1, **sp, **T1, **NX}, "S2＋T1": {**s2, **sp, **T1, **NX},
        "ⓐ閒置 S1": dict(s1), "ⓐ閒置 S2": dict(s2), "ⓐ閒置 T1（＝D2）": dict(T1), "ⓐ閒置 T2（＝D2）": dict(T2),
        "ⓐ閒置 S1＋T1": {**s1, **T1}, "ⓐ閒置 S2＋T1": {**s2, **T1},
        "跌停賣不掉 S1": {**s1, **sp, "stop_block": blk}, "跌停賣不掉 S2": {**s2, **sp, "stop_block": blk},
        "跌停賣不掉 S1＋T1": {**s1, **sp, **T1, **NX, "stop_block": blk}, "跌停賣不掉 S2＋T1": {**s2, **sp, **T1, **NX, "stop_block": blk},
        "D1 T1": {**T1, **NX, "nx_order": "after"}, "D1 T2": {**T2, **NX, "nx_order": "after"},
        "D1 S1＋T1": {**s1, **sp, **T1, **NX, "nx_order": "after"}, "D1 S2＋T1": {**s2, **sp, **T1, **NX, "nx_order": "after"},
        "D2 S1＋T1": {**s1, **sp, **T1}, "D2 S2＋T1": {**s2, **sp, **T1}}
    EXTRA["臂的參數（不含價格陣列）"] = {k: {kk: (vv if not isinstance(vv, dict) or kk.endswith("rule") else f"<{kk}>") for kk, vv in v.items()}
                                   for k, v in CELLS.items()}
    xmap = {(s, int(e)): int(x) for s, e, x in zip(sig["sid"], sig["entry_pos"], sig["xpos_H120"])}
    rows = []; base_sha = {}
    for r in range(seeds):
        o = L.sim(ctx, {}, r, eng=R)
        base_sha[r] = hashlib.sha256(np.asarray(o["equity"], float).tobytes()).hexdigest()
    for name, kw in CELLS.items():
        for r in range(seeds):
            au = []
            o = L.sim(ctx, kw, r, eng=R, audit=au); o["_audit"] = au
            eq = np.asarray(o["equity"], float); hv = np.asarray(o["hold_val"], float)
            cf = (eq[w0:w1 + 1] - hv[w0:w1 + 1]) / eq[w0:w1 + 1]
            pos = {}; stops = []; buys = []; px_in = {}; rb_ret = []
            for a in au:
                if a["side"] == "buy":
                    pos[a["sid"]] = int(a["t"]); buys.append((int(a["t"]), a["sid"])); px_in[(a["sid"], int(a["t"]))] = float(a["px"])
                elif "kind" not in a:
                    e = pos.pop(a["sid"])
                    if int(a["t"]) < xmap[(a["sid"], e)]:
                        stops.append((int(a["t"]), a["sid"]))
                    for ts, s in stops:                 # 停損後 20 日內又買回的那一筆 ⇒ 它自己的價格報酬（出場價 ÷ 進場價 − 1）
                        if s == a["sid"] and 0 <= e - ts <= 20 and (e, s) not in [(q[0], q[1]) for q in rb_ret]:
                            rb_ret.append((e, s, float(a["px"]) / px_in[(s, e)] - 1.0))
            rebuy = sum(any(s2 == s and 0 <= tb - ts <= 20 for tb, s2 in buys) for ts, s in stops)
            w = np.asarray(o.get("x_nx_waits", []), float)
            nxsz = [float(a["amt"]) / (float(a["equity_prev"]) / 10) for a in au if a.get("kind") == "nx" and a["equity_prev"] > 0]
            rr_ = np.asarray([q[2] for q in rb_ret], float)
            rows.append({"臂": name, "r": r, "與原樣不同": hashlib.sha256(eq.tobytes()).hexdigest() != base_sha[r],
                         "停損出場": int(o.get("sl_exits", 0)), "賣半": int(o.get("x_trim_n", 0)), "部位數": int(o["trades"]),
                         "待買_停損產生": int(o.get("x_nx_stop_lots", 0)), "待買買進": int(o.get("x_nx_n", 0)),
                         "槽滿等（天次）": int(o.get("x_nx_full_days", 0)), "期末未買": int(o.get("x_nx_pending_end", 0)),
                         "等待_中位": float(np.median(w)) if len(w) else None, "等待_p90": float(np.percentile(w, 90)) if len(w) else None,
                         "等待_最長": int(w.max()) if len(w) else None,
                         "現金比例_均值": round(float(cf.mean()), 4), "現金比例_中位": round(float(np.median(cf)), 4),
                         "待買部位占權益_中位": round(_nx_frac(o, ctx["closes"], w0, w1), 4),
                         "待買部位大小占slot_中位": round(float(np.median(nxsz)), 4) if nxsz else None,
                         "待買部位大小占slot_均值": round(float(np.mean(nxsz)), 4) if nxsz else None,
                         "停損後20日內又買回同檔": int(rebuy), "又買回那幾筆的報酬_均值": round(float(rr_.mean()), 4) if len(rr_) else None,
                         "又買回那幾筆的報酬_中位": round(float(np.median(rr_)), 4) if len(rr_) else None,
                         "停損擋賣天次": int(o["sl_block_days"]) if "sl_block_days" in o else None})
            del o, eq, hv
        g = [z for z in rows if z["臂"] == name]
        print(f"  {name}：" + "｜".join(f"r{z['r']} 停損 {z['停損出場']} 賣半 {z['賣半']} 待買 {z['待買買進']} 等中位 {z['等待_中位']} "
                                       f"現金均 {z['現金比例_均值']} 待買占 {z['待買部位占權益_中位']} 待買/slot {z['待買部位大小占slot_中位']} "
                                       f"再買回 {z['停損後20日內又買回同檔']}" + (f" 擋賣 {z['停損擋賣天次']}" if z["停損擋賣天次"] is not None else "")
                                       for z in g), flush=True)
    D_ = pd.DataFrame(rows)
    main6 = D_[D_["臂"].isin(["S1", "S2", "T1", "T2", "S1＋T1", "S2＋T1"])]
    chk(f"6 格 × {seeds} 顆都與 #1 原樣不同、每格每顆都有觸發（停損或賣半）與待買買進",
        bool(main6["與原樣不同"].all() and ((main6["停損出場"] + main6["賣半"]) > 0).all() and (main6["待買買進"] > 0).all()))
    blkd = D_[D_["臂"].str.startswith("跌停賣不掉")]
    chk("描述：跌停賣不掉版每顆都有被擋的停損天次（stop_block 確實作用）", bool((blkd["停損擋賣天次"] > 0).all()), repr(blkd["停損擋賣天次"].tolist()))
    idle = D_[D_["臂"].str.startswith("ⓐ")]
    chk("描述 ⓐ 閒置版：沒有待買（x_nx 鍵不存在 ⇒ 0）", bool((idle["待買買進"] == 0).all()))
    EXTRA["逐顆"] = rows
    keys = ("停損出場", "賣半", "待買買進", "槽滿等（天次）", "期末未買", "等待_中位", "等待_p90", "現金比例_均值", "現金比例_中位",
            "待買部位占權益_中位", "待買部位大小占slot_中位", "停損後20日內又買回同檔", "又買回那幾筆的報酬_中位", "停損擋賣天次")
    agg = D_.groupby("臂", sort=False)[list(keys)].median()
    EXTRA["各臂 5 顆中位"] = agg.reset_index().to_dict("records")
    with pd.option_context("display.width", 250, "display.max_columns", 30):
        print(agg.to_string())

if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "all"
    os.chdir(REPO)
    t0 = time.time(); fails = 0; ctx = None
    for m_, fn in (("fixtures", fixtures), ("gate1", gate1), ("gate2", gate2), ("t1gate", t1gate), ("nonid", nonid)):
        if mode in (m_, "all"):
            RESULTS.clear(); EXTRA.clear()
            if m_ == "t1gate":
                ctx = fn()
            elif m_ == "nonid":
                fn(ctx)
            else:
                fn()
            dump(m_); fails += sum(not r["ok"] for r in RESULTS)
    print(f"完成（{time.time() - t0:.0f}s）")
    sys.exit(1 if fails else 0)

# -*- coding: utf-8 -*-
"""PREREGP9 seq8 §六 引擎擴充（research11.simulate_mtm 五個新參數）的 fixture 與兩道回歸閘。回測線，2026-09-25。

    python3 backtest/selftest_p9engine.py fixtures   # 手算小例子、無前視、鑑別力（突變體必須被抓到）、全關＝原引擎
    python3 backtest/selftest_p9engine.py gate1      # 回歸閘 1：regress_tradability(18)＋regress_delist(6)＋改前／改後 A/B 矩陣＋AFC W1 既有結果
    python3 backtest/selftest_p9engine.py gate2      # 回歸閘 2：researchp9 原資料＋原窗重現 base 臂（＋b 臂、P7 既有結果）
    python3 backtest/selftest_p9engine.py nonid      # ⛔ 不是恆等輸出：每個新參數開啟 ⇒ 與全關不同（真資料、有觸發）
    python3 backtest/selftest_p9engine.py all

⭐ 改前的引擎一律從 git 物件庫取（blob ORIG_BLOB ＝ 改動前 HEAD:backtest/research11.py），⛔ 不靠工作目錄裡的副本。
⭐ 突變體（鑑別力）：把新程式碼裡所有標了 `# _XLAG` 的 `[t - 1]` 換成 `[t]`（＝判定改用 t 當日）⇒ 無前視測試必須抓到。
⛔ 本檔【不跑 P9 的 12 格】、⛔ 不報任何新參數的年化／回落（那要等裁定線收下引擎才跑）；nonid 只報「與全關不同」與觸發次數。
結果寫到 backtest/resultsp9_engine/*.json。
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import types

import numpy as np
import pandas as pd

REPO = os.path.expanduser("~/tw-p17")
OUT = os.path.join(REPO, "backtest", "resultsp9_engine")
PY = sys.executable
ORIG_BLOB = "664e2ea276d42776286720324791d293ce326766"      # 改動前 HEAD:backtest/research11.py（git rev-parse HEAD:backtest/research11.py）
P9_COMMIT = "0dc5d62b2a"                                     # 產出 backtest/resultsp9/cells.csv 的 commit（PREREGP9 2-C ⓑ 跑完）
P9_ARCHIVE = os.path.expanduser(f"~/p9data/{P9_COMMIT}")     # git archive 0dc5d62b2a backtest data/meta data/stocks data/adj（唯讀）
P9_RUN = os.path.expanduser(f"~/p9run/{P9_COMMIT}")          # 可寫的執行目錄：archive 的 backtest 副本＋data 連結＋新引擎
RESULTS = []


def chk(name, cond, detail=""):
    RESULTS.append({"name": name, "ok": bool(cond), "detail": detail})
    print(("  ✓ " if cond else "  ✗ ") + name + (f"｜{detail}" if detail else ""), flush=True)
    return bool(cond)


def dump(tag):
    os.makedirs(OUT, exist_ok=True)
    p = os.path.join(OUT, f"{tag}.json")
    json.dump({"when": pd.Timestamp.now(tz="Asia/Taipei").strftime("%Y-%m-%d %H:%M"), "n": len(RESULTS),
               "fail": sum(not r["ok"] for r in RESULTS), "checks": RESULTS}, open(p, "w"), ensure_ascii=False, indent=1)
    print(f"寫入 {p}：{len(RESULTS)} 條，失敗 {sum(not r['ok'] for r in RESULTS)}")


# ─────────────────────────── 引擎載入（新／改前／突變體）
def _load_src(src: str, name: str, file: str):
    import backtest  # noqa: F401  ⭐ 先載入套件，相對 import 才找得到
    mod = types.ModuleType(name)
    mod.__dict__.update({"__package__": "backtest", "__name__": name, "__file__": file})
    exec(compile(src, f"<{name}>", "exec"), mod.__dict__)
    sys.modules[name] = mod
    return mod


def engine_orig():
    src = subprocess.check_output(["git", "-C", REPO, "cat-file", "-p", ORIG_BLOB]).decode("utf-8")
    return _load_src(src, "backtest._r11_orig", os.path.join(REPO, "backtest", "research11.py"))


def engine_mutant():
    """鑑別力用突變體：`# _XLAG` 行的 [t - 1] ⇒ [t]（判定改用 t 當日收盤／狀態 ＝ 前視）。"""
    from backtest import research11 as R
    src = open(R.__file__, encoding="utf-8").read()
    lines = src.split("\n"); n = 0
    for i, ln in enumerate(lines):
        if "# _XLAG" in ln and "[t - 1]" in ln:
            lines[i] = ln.replace("[t - 1]", "[t]"); n += 1
    if n < 6:
        raise SystemExit(f"⛔ 突變點只找到 {n} 個（應 ≥ 6：兩處 below、減半、加碼 gain／flag／hold）")
    return _load_src("\n".join(lines), "backtest._r11_mut", R.__file__), n


def same_out(a: dict, b: dict, skip_prefix=None) -> tuple[bool, str]:
    ka = {k for k in a if not (skip_prefix and k.startswith(skip_prefix))}
    kb = {k for k in b if not (skip_prefix and k.startswith(skip_prefix))}
    if ka != kb:
        return False, f"鍵不同 {sorted(ka ^ kb)}"
    for k in sorted(ka):
        va, vb = a[k], b[k]
        if isinstance(va, np.ndarray) or isinstance(vb, np.ndarray):
            va, vb = np.asarray(va), np.asarray(vb)
            if va.dtype != vb.dtype or va.shape != vb.shape or va.tobytes() != vb.tobytes():
                return False, f"{k} 陣列不同"
        elif repr(va) != repr(vb):
            return False, f"{k}: {va!r} vs {vb!r}"
    return True, ""


# ─────────────────────────── fixture 的小世界
NC = 100


def px(*segs, default=10.0):
    """segs：(起, 迄, 開盤, 收盤)，迄不含。回 (opens, closes)。"""
    o = np.full(NC, default, float); c = np.full(NC, default, float)
    for s, e, ov, cv in segs:
        o[s:e] = ov; c[s:e] = cv
    return o, c


def mksig(rows, closes, opens):
    return pd.DataFrame([{"sid": s, "entry_pos": e, "xpos_HX": x, "g_HX": float(closes[s][x]) / float(opens[s][e]) - 1.0}
                         for s, e, x in rows])


def run(R, rows, prices, N, audit=True, seed=0, **kw):
    closes = {s: p[1] for s, p in prices.items()}; opens = {s: p[0] for s, p in prices.items()}
    au = [] if audit else None
    out = R.simulate_mtm(mksig(rows, closes, opens), "HX", N, np.random.default_rng(seed), closes, opens, NC,
                         return_equity=True, audit=au, **kw)
    out["_audit"] = au
    return out


def fin(out):
    return float(out["equity"][out["end"] - 1])


def recs(out, kind=None, t=None):
    return [r for r in out["_audit"] if (kind is None or r.get("kind") == kind) and (t is None or r["t"] == t)]


def trad_of(prices, up=(), dn=(), halt=()):
    """合成 tradable：up／dn ＝ (sid, t) 開盤漲停／跌停；halt ＝ (sid, t) 停牌。"""
    T = {}
    for s in prices:
        T[s] = {"trd": np.ones(NC, bool), "up_o": np.zeros(NC, bool), "dn_o": np.zeros(NC, bool), "dn_c": np.zeros(NC, bool)}
    for s, t in up:
        T[s]["up_o"][t] = True
    for s, t in dn:
        T[s]["dn_o"][t] = True
    for s, t in halt:
        T[s]["trd"][t] = False
    return T


def close_to(a, b, tol=1e-12):
    return abs(a - b) <= tol


def fixtures():
    from backtest import research11 as R
    C = R.COST
    print("── fixture（手算小例子；⭐ 預期值用獨立的算式寫，⛔ 不呼叫引擎的內部函式）")
    # ── 2-A 分批
    pA = {"A": px((0, 30, 10, 10), (30, 50, 11, 11), (50, NC, 12, 12))}
    o = run(R, [("A", 10, 60)], pA, 1, entry_tranches=2)
    exp = (0.5 + 0.5 * 10 / 11) * 1.2 - 1.0 * C
    b = [(r["t"], round(r["amt"], 12), r["px"]) for r in o["_audit"] if r["side"] == "buy"]
    chk("2-A k=2：第 1 份 t=10 買 0.5、第 2 份 t=30（+20 日）以開盤 11 買 0.5；期末 ＝ (0.5+0.5×10/11)×1.2 − 1.0×COST",
        close_to(fin(o), exp) and b == [(10, 0.5, 10.0), (30, 0.5, 11.0)] and o["x_tr_buys"] == 1 and o["x_tr_unbought"] == 0,
        f"期末 {fin(o):.12f} vs 手算 {exp:.12f}；買進 {b}")
    o = run(R, [("A", 10, 60)], pA, 1, entry_tranches=3)
    exp = (1 / 3) * (1.2 + 1.2 * 10 / 11 + 1.2 * 10 / 12) - 1.0 * C
    b = [r["t"] for r in o["_audit"] if r["side"] == "buy"]
    chk("2-A k=3：三份在 t=10／30／50（開盤 10／11／12）各買 1/3；期末手算相符",
        close_to(fin(o), exp) and b == [10, 30, 50] and o["x_tr_buys"] == 2, f"期末 {fin(o):.12f} vs {exp:.12f}；買進日 {b}")
    o = run(R, [("A", 10, 45)], pA, 1, entry_tranches=3)
    exp = 1 / 3 + (1 / 3 + (1 / 3) * 10 / 11) * 1.1 - (2 / 3) * C
    b = [r["t"] for r in o["_audit"] if r["side"] == "buy"]
    chk("2-A k=3、第 45 日出場 ⇒ 第 3 份（t=50）不買、x_tr_unbought=1、那 1/3 留現金",
        close_to(fin(o), exp) and b == [10, 30] and o["x_tr_unbought"] == 1, f"期末 {fin(o):.12f} vs {exp:.12f}；買進日 {b}")
    o = run(R, [("A", 10, 60)], pA, 1, entry_tranches=2, tradable=trad_of(pA, up=[("A", 30)]))
    b = [r["t"] for r in o["_audit"] if r["side"] == "buy"]
    chk("2-A 可交易性：第 2 份那天（t=30）開盤漲停 ⇒ 延到 t=31 開盤買、x_tr_blocked_days=1",
        b == [10, 31] and o["x_tr_blocked_days"] == 1 and close_to(fin(o), (0.5 + 0.5 * 10 / 11) * 1.2 - C), f"買進日 {b}")
    # ── 2-B 加碼
    pG = {"A": px((0, 20, 10, 10), (20, 21, 10, 11.6), (21, 30, 11.8, 11.8), (30, NC, 13, 13))}
    o = run(R, [("A", 10, 60)], pG, 2, add_rule={"kind": "gain", "x": 0.15})
    want = 0.5 * (0.5 + 0.5 * 11.6 / 10) / 2
    exp = (0.5 - want) + (0.5 + want * 10 / 11.8) * 1.3 - (0.5 + want) * C
    ad = [(r["t"], r["px"]) for r in recs(o, "add")]
    chk("2-B ⓐ +15%：收盤[20]=11.6（+16%）⇒ t=21 開盤 11.8 加 0.5×slot（slot＝equity[20]/2）；漲到 +30% 也不再加（只一次）",
        close_to(fin(o), exp) and ad == [(21, 11.8)] and o["x_add_n"] == 1, f"期末 {fin(o):.12f} vs {exp:.12f}；加碼 {ad}")
    pS = {"A": pG["A"], "B": px((0, 15, 10, 10), (15, 16, 10, 1.0), (16, NC, 1.0, 1.0))}
    o = run(R, [("A", 10, 60), ("B", 10, 15)], pS, 2, add_rule={"kind": "gain", "x": 0.15})
    cash = 0.5 * (0.1 - C)
    exp = cash + 0.5 * 1.3 - 0.5 * C
    chk("2-B 現金不足（short='skip'，登錄逐字）：要 0.5 slot、現金只剩 B 賠掉後的 0.047 ⇒ 不加、x_add_short=1",
        close_to(fin(o), exp) and not recs(o, "add") and o["x_add_short"] == 1 and o["x_add_n"] == 0, f"期末 {fin(o):.12f} vs {exp:.12f}")
    o = run(R, [("A", 10, 60), ("B", 10, 15)], pS, 2, add_rule={"kind": "gain", "x": 0.15, "short": "partial"})
    exp = (0.5 + cash * 10 / 11.8) * 1.3 - (0.5 + cash) * C
    ad = [round(r["amt"], 12) for r in recs(o, "add")]
    chk("2-B 現金不足（short='partial'，按比例）：只加得到現金那麼多（0.047）、x_add_short=1",
        close_to(fin(o), exp) and ad == [round(cash, 12)] and o["x_add_short"] == 1, f"期末 {fin(o):.12f} vs {exp:.12f}；加 {ad}")
    pF = {"A": px((0, 26, 10, 10), (26, NC, 10.5, 10.5))}
    fl = np.zeros(NC, bool); fl[[5, 25, 35]] = True
    o = run(R, [("A", 10, 60)], pF, 2, add_rule={"kind": "flag", "flags": {"A": fl}})
    exp = 0.25 + (0.5 + 0.25 * 10 / 10.5) * 1.05 - 0.75 * C
    ad = [r["t"] for r in recs(o, "add")]
    chk("2-B ⓑ 旗標：進場前（t=5）的旗標不算；flags[25] ⇒ t=26 加；flags[35] 不再加",
        close_to(fin(o), exp) and ad == [26] and o["x_add_n"] == 1, f"期末 {fin(o):.12f} vs {exp:.12f}；加碼日 {ad}")
    pH = {"A": px((0, 41, 10, 10), (41, NC, 10.5, 10.5))}
    o = run(R, [("A", 10, 60)], pH, 2, add_rule={"kind": "hold", "days": 40})
    want = 0.5 * (0.5 + 0.5 * 1.05) / 2
    exp = (0.5 - want) + (0.5 + want * 10 / 10.5) * 1.05 - (0.5 + want) * C
    ad = [r["t"] for r in recs(o, "add")]
    chk("2-B ⓒ 持有滿 40 根（t0=10 ⇒ 第 40 根＝t=49）收盤 10.5 > 10 ⇒ t=50 開盤加；只一次",
        close_to(fin(o), exp) and ad == [50] and o["x_add_n"] == 1, f"期末 {fin(o):.12f} vs {exp:.12f}；加碼日 {ad}")
    pH2 = {"A": px((0, 41, 10, 10), (41, NC, 10.5, 10.5), (49, 50, 9.9, 9.9))}
    o = run(R, [("A", 10, 60)], pH2, 2, add_rule={"kind": "hold", "days": 40})
    chk("2-B ⓒ 第 40 根那天收盤 9.9 ≤ 進場價 ⇒ 不加；之後回到 10.5 也不加（只在那一天判一次）",
        not recs(o, "add") and o["x_add_trig"] == 0 and close_to(fin(o), 0.5 + 0.5 * 1.05 - 0.5 * C), f"期末 {fin(o):.12f}")
    # ── 2-C ⓐ 個股減半
    pT = {"A": px((0, 20, 10, 10), (20, 21, 10, 8.9), (21, 30, 8.8, 8.8), (30, NC, 7, 7))}
    o = run(R, [("A", 10, 60)], pT, 1, trim_rule={"x": 0.10, "frac": 0.5})
    exp = 0.5 * 0.88 - 0.5 * C + 0.5 * 0.7 - 0.5 * C
    tr = [(r["t"], r["px"], round(r["cost"], 15)) for r in recs(o, "trim")]
    chk("2-C ⓐ −10%：收盤[20]=8.9（−11%）⇒ t=21 開盤 8.8 賣一半（成本 0.5×COST）；跌到 −30% 不再賣；期末 ＝ 0.79 − COST",
        close_to(fin(o), exp) and tr == [(21, 8.8, round(0.5 * C, 15))] and o["x_trim_n"] == 1, f"期末 {fin(o):.12f} vs {exp:.12f}；{tr}")
    o = run(R, [("A", 10, 60)], pT, 1, trim_rule={"x": 0.10, "frac": 0.5}, tradable=trad_of(pT, dn=[("A", 21)]))
    tr = [r["t"] for r in recs(o, "trim")]
    chk("2-C ⓐ 可交易性：t=21 開盤跌停 ⇒ t=22 開盤賣、x_trim_blocked_days=1", tr == [22] and o["x_trim_blocked_days"] == 1
        and close_to(fin(o), exp), f"賣出日 {tr}")
    # ── 2-C ⓑⓒⓓⓔ 新部位倍數
    below = np.zeros(NC, bool); below[20:40] = True
    pM = {"A": px(), "B": px()}
    o = run(R, [("A", 10, 60), ("B", 25, 60)], pM, 2, size_mult_by_regime={"mult": 0.5, "below": below})
    bb = [(r["t"], round(r["amt"], 12)) for r in o["_audit"] if r["side"] == "buy"]
    chk("2-C ⓓⓔ 型（0.5）：A 在線上 t=10 買 0.5；B 在 t=25（below[24] 真）只買 0.5×slot＝0.25；m̄ 名目＝0.75",
        bb == [(10, 0.5), (25, 0.25)] and close_to(fin(o), 1 - 0.75 * C) and o["x_mbar_nominal"] == 0.75, f"買進 {bb}")
    wk = np.zeros(NC, bool); wk[1:] = below[:-1]
    o2 = run(R, [("A", 10, 60), ("B", 25, 60)], pM, 2, weak=wk, weak_size=0.5)
    ok, why = same_out(o, o2, skip_prefix="x_")
    chk("2-C ⓑ 共用：size_mult_by_regime(mult 0.5, below) 與既有 weak（below 平移一天）、weak_size 0.5 逐位元相同（x_ 鍵除外）", ok, why)
    pM2 = {"A": px((0, 20, 10, 10), (20, NC, 8, 8)), "B": px()}
    o = run(R, [("A", 10, 60), ("B", 25, 60)], pM2, 2, size_mult_by_regime={"mult": 1.5, "below": below})
    exp = (0.5 - 0.45) + 0.5 * 0.8 - 0.5 * C + 0.45 - 0.45 * C
    bb = [round(r["amt"], 12) for r in o["_audit"] if r["side"] == "buy"]
    chk("2-C ⓒ 1.5 slot、現金不足（skip，照 2-B）：slot＝0.45、要 0.675、現金 0.5 ⇒ 只買 1 slot＝0.45、x_mult_short=1",
        close_to(fin(o), exp) and bb == [0.5, 0.45] and o["x_mult_short"] == 1, f"期末 {fin(o):.12f} vs {exp:.12f}；買 {bb}")
    o = run(R, [("A", 10, 60), ("B", 25, 60)], pM2, 2, size_mult_by_regime={"mult": 1.5, "below": below, "short": "partial"})
    exp = 0.5 * 0.8 - 0.5 * C + 0.5 - 0.5 * C
    bb = [round(r["amt"], 12) for r in o["_audit"] if r["side"] == "buy"]
    chk("2-C ⓒ 1.5 slot、現金不足（partial）⇒ 買光現金 0.5、x_mult_short=1", close_to(fin(o), exp) and bb == [0.5, 0.5], f"買 {bb}")
    o = run(R, [("A", 10, 60), ("B", 25, 60)], pM, 4, size_mult_by_regime={"mult": 1.5, "below": below})
    bb = [round(r["amt"], 12) for r in o["_audit"] if r["side"] == "buy"]
    chk("2-C ⓒ 1.5 slot、現金夠：N=4 ⇒ A 0.25（線上）、B 0.375（線下）", bb == [0.25, 0.375] and o["x_mult_short"] == 0
        and close_to(fin(o), 1 - 0.625 * C), f"買 {bb}")
    # ── 2-C ⓕⓖⓗ regime_trim
    belR = np.zeros(NC, bool); belR[20:30] = True           # below[20..29] ⇒ t=21 開盤賣半；below[30] 假 ⇒ t=31 開盤補回
    pR = {"A": px((0, 21, 10, 10), (21, 31, 9, 9), (31, NC, 12, 12)), "B": px(), "C": px((0, 31, 10, 10), (31, NC, 11, 11))}
    o = run(R, [("A", 10, 60), ("B", 10, 25), ("C", 26, 60)], pR, 2, regime_trim={"hold": 0.5, "below": belR})
    cash = 0.25 * 0.9 + 0.25 - 0.5 * C                     # t=21 兩檔各賣一半
    cash += 0.25 - 0.25 * C                                 # t=25 B 出場（剩半份、成本基礎 0.25）
    amtC = 0.5 * ((cash + 0.25 * 0.9) / 2)                  # t=26 線下新部位只買半份（slot＝equity[25]/2）
    cash -= amtC
    nA, nC = 0.25 * 12 / 10, amtC * 11 / 10                 # t=31 補回：買回與目前同樣多的股數
    s = cash / (nA + nC)
    exp = (0.25 + nA * s * 10 / 12) * 1.2 - (0.25 + nA * s) * C + (amtC + nC * s * 10 / 11) * 1.1 - (amtC + nC * s) * C
    rs = sorted((r["t"], r["sid"]) for r in recs(o, "rt_sell")); rf = sorted((r["t"], r["sid"]) for r in recs(o, "rt_refill"))
    chk("2-C ⓕ：跌破次日（t=21）A、B 各賣一半；線下新部位 C 只買半份；站回次日（t=31）補回 A、C；B 已出場不補",
        rs == [(21, "A"), (21, "B")] and rf == [(31, "A"), (31, "C")] and o["x_rt_sell_n"] == 2 and o["x_rt_refill_n"] == 2,
        f"賣半 {rs}；補回 {rf}")
    chk("2-C ⓕ 現金不足：補回需求 {:.4f} > 現金 {:.4f} ⇒ 兩檔按同一比例 {:.4f} 少補、x_rt_refill_short=1；期末手算相符".format(nA + nC, cash, s),
        s < 1 and o["x_rt_refill_short"] == 1 and close_to(o["x_rt_refill_fill_min"], s) and close_to(fin(o), exp),
        f"期末 {fin(o):.12f} vs {exp:.12f}")
    fr = {r["sid"]: r["amt"] for r in recs(o, "rt_refill")}
    chk("2-C ⓕ 同一比例：A、C 補回金額 ÷ 各自需求 相同", close_to(fr["A"] / nA, fr["C"] / nC), f"{fr['A'] / nA:.15f} vs {fr['C'] / nC:.15f}")
    pR1 = {"A": pR["A"]}
    o = run(R, [("A", 10, 60)], pR1, 4, regime_trim={"hold": 0.5, "below": belR})
    exp = (0.75 + 0.125 * 0.9 - 0.125 * C - 0.15) + 0.25 * 1.2 - (0.125 + 0.15) * C
    rf = [(r["t"], round(r["amt"], 12)) for r in recs(o, "rt_refill")]
    chk("2-C ⓕ 現金夠：t=31 補回 0.15（＝0.125 名目 × 12/10）⇒ 股數回到賣出前、x_rt_refill_short=0；期末手算相符",
        close_to(fin(o), exp) and rf == [(31, 0.15)] and o["x_rt_refill_short"] == 0, f"期末 {fin(o):.12f} vs {exp:.12f}；補回 {rf}")
    o = run(R, [("A", 10, 60)], pR1, 4, regime_trim={"hold": 0.5, "below": belR}, tradable=trad_of(pR1, dn=[("A", 21)]))
    rs = [r["t"] for r in recs(o, "rt_sell")]
    chk("2-C ⓕ 可交易性：t=21 開盤跌停 ⇒ t=22 賣半、x_rt_blocked_days=1", rs == [22] and o["x_rt_blocked_days"] == 1, f"賣半日 {rs}")
    # ── regime_below 本身
    b = np.array([10, 11, 12, 11, 9, 13, 14, 12, np.nan, 15], float)
    got = R.regime_below(b, 3)
    ref = np.array([False, False] + [bool(b[i] < np.mean(b[i - 2:i + 1])) if np.isfinite(b[i - 2:i + 1]).all() else False for i in range(2, 10)])
    chk("regime_below：below[i] ＝ 收盤[i] < 含第 i 天的 MA_n；暖身與缺值 ⇒ False", np.array_equal(got, ref), f"{got.astype(int).tolist()}")
    # ── 全關／k=1／開了但沒觸發 ⇒ 與原引擎相同
    R0 = engine_orig()
    pZ = {"A": pG["A"], "B": pS["B"], "C": pR["C"]}
    rows = [("A", 10, 60), ("B", 10, 15), ("C", 20, 70)]
    a = run(R0, rows, pZ, 2); z = run(R, rows, pZ, 2)
    ok, why = same_out({k: v for k, v in a.items() if k != "_audit"}, {k: v for k, v in z.items() if k != "_audit"})
    chk("全關 ⇒ 與改前引擎（git blob）逐位元相同（equity bytes＋全部回傳＋audit）", ok and repr(a["_audit"]) == repr(z["_audit"]), why)
    z1 = run(R, rows, pZ, 2, entry_tranches=1)
    ok, why = same_out({k: v for k, v in a.items() if k != "_audit"}, {k: v for k, v in z1.items() if k != "_audit"})
    chk("entry_tranches=1 ＝ 關閉 ⇒ 與改前引擎逐位元相同", ok, why)
    for nm, kw in (("add gain x=1e9", dict(add_rule={"kind": "gain", "x": 1e9})),
                   ("trim x=0.999", dict(trim_rule={"x": 0.999, "frac": 0.5})),
                   ("mult 0.5、below 全假", dict(size_mult_by_regime={"mult": 0.5, "below": np.zeros(NC, bool)})),
                   ("regime_trim、below 全假", dict(regime_trim={"hold": 0.5, "below": np.zeros(NC, bool)}))):
        zz = run(R, rows, pZ, 2, **kw)
        ok, why = same_out({k: v for k, v in a.items() if k != "_audit"}, {k: v for k, v in zz.items() if k != "_audit"}, skip_prefix="x_")
        chk(f"擴充路徑開著但沒有觸發（{nm}）⇒ 與改前引擎逐位元相同（x_ 鍵除外）", ok, why)
    # ── 無前視＋鑑別力
    lookahead(R, engine_mutant())
    # ── 參數防呆
    for nm, kw in (("兩個一起開", dict(entry_tranches=2, trim_rule={"x": 0.1})), ("與 weak 同開", dict(entry_tranches=2, weak=np.zeros(NC, bool))),
                   ("與 stop 同開", dict(entry_tranches=2, stop=("fix", 0.1))), ("k=0", dict(entry_tranches=0)),
                   ("add kind 打錯", dict(add_rule={"kind": "gian"})), ("hold=1", dict(regime_trim={"hold": 1.0, "below": below}))):
        try:
            run(R, rows, pZ, 2, **kw); ok = False
        except ValueError:
            ok = True
        chk(f"防呆：{nm} ⇒ ValueError", ok)


def lookahead(R, mut):
    """改 t=s 以後的價格／狀態 ⇒ 正確引擎在 t ≤ s 的交易與 equity[:s] 都不變；突變體（判定改用 t 當日）必須被抓到。"""
    R_, n_mut = mut
    print(f"── 無前視＋鑑別力（突變體：{n_mut} 個 `# _XLAG` 讀取點改成 [t]）")

    def pair(eng, rowsA, pa, pb, N, kwa, kwb, s):
        oa = run(eng, rowsA, pa, N, **kwa); ob = run(eng, rowsA, pb, N, **kwb)
        ta = [r for r in oa["_audit"] if r["t"] <= s]; tb = [r for r in ob["_audit"] if r["t"] <= s]
        pre = repr(ta) == repr(tb) and oa["equity"][:s].tobytes() == ob["equity"][:s].tobytes()
        post = repr(oa["_audit"]) != repr(ob["_audit"])
        return pre, post

    s = 30
    cases = []
    bA = np.full(NC, 100.0); bB = bA.copy(); bB[s:] = 80.0     # 0050 在 t=30 急跌 ⇒ below(MA3)[30] 在 B 版為真
    base = {"A": px(), "B": px()}
    cases.append(("regime_trim（0050 MA3，引擎自算 below）", [("A", 10, 60)], base, base, 2,
                  dict(regime_trim={"hold": 0.5, "ma": 3, "bench": bA}), dict(regime_trim={"hold": 0.5, "ma": 3, "bench": bB})))
    cases.append(("size_mult_by_regime（0050 MA3；B 在 t=30、C 在 t=31 進場）", [("A", 10, 60), ("B", s, 70), ("C", s + 1, 70)], dict(base, C=px()), dict(base, C=px()), 3,
                  dict(size_mult_by_regime={"mult": 0.5, "ma": 3, "bench": bA}), dict(size_mult_by_regime={"mult": 0.5, "ma": 3, "bench": bB})))
    pT = {"A": px()}; pT2 = {"A": px((s, s + 1, 10, 8), (s + 1, NC, 8, 8))}   # ⭐ 只改 t=s 的【收盤】與 s+1 起的開盤（t=s 的開盤在 t 當下已知）
    cases.append(("trim_rule（個股收盤 t=30 起 −20%）", [("A", 10, 60)], pT, pT2, 1, dict(trim_rule={"x": 0.1}), dict(trim_rule={"x": 0.1})))
    pG2 = {"A": px((s, s + 1, 10, 12), (s + 1, NC, 12, 12))}
    cases.append(("add_rule gain（個股收盤 t=30 起 +20%）", [("A", 10, 60)], pT, pG2, 2,
                  dict(add_rule={"kind": "gain", "x": 0.15}), dict(add_rule={"kind": "gain", "x": 0.15})))
    fa = np.zeros(NC, bool); fb = fa.copy(); fb[s] = True
    cases.append(("add_rule flag（flags[30] 只在 B 版為真）", [("A", 10, 60)], pT, pT, 2,
                  dict(add_rule={"kind": "flag", "flags": {"A": fa}}), dict(add_rule={"kind": "flag", "flags": {"A": fb}})))
    pH_a = {"A": px((41, NC, 11, 11))}; pH_b = {"A": px((41, s + 20, 11, 11), (s + 20, s + 21, 11, 9), (s + 21, NC, 9, 9))}   # t0=10、第 40 根＝t=49；改 t=50 的收盤起
    for nm, rows, pa, pb, N, kwa, kwb in cases + [("add_rule hold（改 t=50 起的收盤）", [("A", 10, 60)], pH_a, pH_b, 2,
                                                   dict(add_rule={"kind": "hold", "days": 40}), dict(add_rule={"kind": "hold", "days": 40}))]:
        ss = s + 20 if "hold" in nm else s
        pre, post = pair(R, rows, pa, pb, N, kwa, kwb, ss)
        chk(f"無前視 {nm}：t ≤ {ss} 的交易與 equity[:{ss}] 不變、之後確實不同（修改不是空的）", pre and post, f"前段相同 {pre}／後段不同 {post}")
        mpre, _ = pair(R_, rows, pa, pb, N, kwa, kwb, ss)
        chk(f"鑑別力 {nm}：突變體（判定用 t 當日）⇒ 前段就不同（被抓到）", not mpre, f"突變體前段相同 {mpre}")
    # 呼叫端前視（below 平移一天）也要抓得到
    blA = R.regime_below(bA, 3); blB = R.regime_below(bB, 3)
    pre, _ = pair(R, [("A", 10, 60)], base, base, 2, dict(regime_trim={"hold": 0.5, "below": np.roll(blA, -1)}),
                  dict(regime_trim={"hold": 0.5, "below": np.roll(blB, -1)}), s)
    chk("鑑別力（呼叫端前視）：把 below 往前平移一天再傳入 ⇒ 前段就不同（被抓到）", not pre)


# ─────────────────────────── 真資料（tw-p17 工作樹）
def load_real():
    from backtest import data as D, researchp7 as P7, researchp1 as P1, p4_features as P4F
    cal = D.load_calendar(); ncal = len(cal)
    uni = D.load_universe().set_index("stock_id")["market"]
    panel = P4F.read_panel(os.path.join(REPO, "backtest", "resultsp4", "panel.csv.gz"))
    closes, opens = P1.load_prices(set(panel["stock_id"]), cal, uni)
    sig = P7.build_sig_gate_b(panel, cal, closes, opens)
    bench = pd.Series(D.load_stock("0050", "twse", cal).df["close"].to_numpy()).ffill().to_numpy(float)
    return cal, ncal, uni, panel, closes, opens, sig, bench


def gate1():
    print("── 回歸閘 1-a：既有兩道回歸閘（新參數全關）")
    for scr, n in (("regress_tradability.py", 18), ("regress_delist.py", 6)):
        p = subprocess.run([PY, os.path.join(REPO, "backtest", scr), "check"], cwd=REPO, capture_output=True, text=True)
        tail = [ln for ln in p.stdout.strip().split("\n") if ln][-1:] if p.stdout else []
        chk(f"{scr} check（{n} 組）逐位元相同", p.returncode == 0 and "✅" in p.stdout, " ".join(tail) + (p.stderr[-300:] if p.returncode else ""))
    print("── 回歸閘 1-b：改前（git blob）／改後 A/B 矩陣（真資料、門檻B、H120、N=8、種子 0,1；比全部回傳＋log＋audit）")
    from backtest import research11 as R
    from backtest import tradability as T
    R0 = engine_orig()
    cal, ncal, uni, panel, closes, opens, sig, bench = load_real()
    trad = T.build(set(sig["sid"]), cal); dl = T.delist_status(trad, cal, official=T.load_official())
    wk = np.zeros(ncal, bool); wk[1:] = R.regime_below(bench, 60)[:-1]
    caps = np.full(ncal, 8, int); caps[1500:1700] = 5
    sl = {(r.sid, int(r.entry_pos)): (int(r.entry_pos), np.full(130, float(opens[r.sid][int(r.entry_pos)]) * 0.85))
          for r in sig.itertuples()}
    CFG = {"plain": {}, "stop_fix": dict(stop=("fix", 0.10)), "stop_trail": dict(stop=("trail", 0.15)), "log": dict(_log=True),
           "queue": dict(d_max=2, queue_days=3, _log=True), "bench": dict(cash_mode="bench", bench=bench),
           "weak_maxw": dict(weak=wk, weak_size=0.5, report_maxw=True, maxw_detail=True),
           "weight_fn": dict(weight_fn=lambda batch, t, eq, cash: [eq / 8 * (1.0 + 0.1 * (i % 2)) for i in range(len(batch))]),
           "caps": dict(n_slots=caps), "cap_fn": dict(cap_fn=lambda sid, t, hs: not (str(sid).startswith("2") and len(hs) >= 4), _log=True),
           "pick": dict(pick="relvol"), "tradable": dict(tradable=trad), "tradable_delist": dict(tradable=trad, delist=dl, _audit=True, _log=True),
           "stop_line": dict(stop_line=sl, tradable=trad)}
    n_ok = 0; n_all = 0
    for name, cfg in CFG.items():
        for seed in (0, 1):
            outs = []
            for eng in (R0, R):
                kw = dict(cfg); lg = [] if kw.pop("_log", False) else None; au = [] if kw.pop("_audit", False) else None
                N = kw.pop("n_slots", 8)
                if name == "pick":
                    kw["pick"] = "relvol"
                o = eng.simulate_mtm(sig, "H120", N, np.random.default_rng(seed), closes, opens, ncal, return_equity=True, log=lg, audit=au, **kw)
                outs.append((o, repr(lg), repr(au)))
            ok, why = same_out(outs[0][0], outs[1][0])
            ok = ok and outs[0][1] == outs[1][1] and outs[0][2] == outs[1][2]
            n_all += 1; n_ok += ok
            if not ok:
                chk(f"A/B {name}/{seed}", False, why)
    chk(f"A/B 矩陣：{len(CFG)} 種既有參數組合 × 2 種子 ＝ {n_all} 組，改前／改後逐位元相同（equity bytes、全部回傳鍵、log、audit）",
        n_ok == n_all, f"{n_ok}/{n_all}")
    print("── 回歸閘 1-c：AFC W1 既有結果（resultsAFC/w1_1000.csv）用原參數重跑（子行程；edc6f8002f 快照）")
    p = subprocess.run([PY, os.path.abspath(__file__), "_afc"], cwd=REPO, capture_output=True, text=True)
    print(p.stdout[-2000:]); print(p.stderr[-2000:]) if p.returncode else None
    try:
        sub = json.load(open(os.path.join(OUT, "_afc.json")))
        for r in sub:
            chk(r["name"], r["ok"], r["detail"])
    except Exception as e:  # noqa: BLE001
        chk("AFC 子行程", False, repr(e))


def _afc(n_seeds=40):
    """AFC 的 W1（P12 (S1,C1,T1)＋tradable＋delist、1,000 顆種子）⇒ 取前 n_seeds 顆逐位元重現。"""
    sys.path.insert(0, REPO); sys.path.insert(0, os.path.join(REPO, "backtest"))
    from backtest import researchAFC as AFC        # ⭐ 內含 researchH2 ⇒ D.DATA 指到 ~/h2data/edc6f8002f…/data
    from backtest import research13 as R13, research11 as R
    D, P7, P12, P4F, T = AFC.D, AFC.P7, AFC.P12, AFC.P4F, AFC.T
    assert "h2data" in D.DATA, D.DATA
    assert hasattr(R, "regime_below"), "⛔ 跑到的不是新引擎"
    cal = D.load_calendar(); ncal = len(cal)
    panel = P4F.read_panel(os.path.join(AFC.OUT, "panel.csv.gz"))
    uni = D.load_universe().set_index("stock_id")["market"]
    closes, opens = {}, {}
    for s in sorted(set(panel["stock_id"])) + ["0050"]:
        st = D.load_stock(s, uni.get(s, "twse"), cal)
        if st is None:
            continue
        c = st.df["close"].to_numpy(float)
        closes[s] = pd.Series(c).ffill().to_numpy(); opens[s] = st.df["open"].to_numpy(float)
    w0, w1 = P12.win_bounds(cal, "全窗"); marks = P12.month_marks(cal, w0, w1)
    c50 = closes["0050"]; eq50 = c50 / c50[w0]
    c50_cagr, c50_mdd = R13.window_stats(eq50, w0, w1 + 1, w0, w1 + 1)
    sig = P7.build_sig_gate_b(panel, cal, closes, opens, start=P12.START, signal="B")
    sig = sig.sort_values(["entry_pos", "sid"], kind="stable").reset_index(drop=True)
    trad = T.build(set(sig["sid"]), cal); dl = T.delist_status(trad, cal, official=T.load_official())
    AFC._init({"closes": closes, "opens": opens, "ncal": ncal, "trad": trad, "dl": dl, "w0": w0, "w1": w1, "marks": marks,
               "c50": c50_cagr, "m50": c50_mdd, "sig": sig})
    ref = pd.read_csv(os.path.join(AFC.OUT, "w1_1000.csv"), float_precision="round_trip").set_index("seed")
    bad = []; n = 0
    for r in range(n_seeds):
        seed = AFC.SEED0 + r
        st = AFC._w1(seed); n += 1
        for k in ("cagr", "mdd", "tr", "expo", "pass"):
            if repr(float(st[k])) != repr(float(ref.loc[seed, k])):
                bad.append((seed, k, st[k], ref.loc[seed, k]))
    out = [{"name": f"AFC W1 既有結果：前 {n} 顆種子（{AFC.SEED0}+r）的 cagr／mdd／tr／expo／pass 與 w1_1000.csv 逐位元相同",
            "ok": not bad, "detail": f"不同 {len(bad)} 項 {bad[:3]}"}]
    json.dump(out, open(os.path.join(OUT, "_afc.json"), "w"), ensure_ascii=False, indent=1)
    print(out)


def gate2():
    print(f"── 回歸閘 2：researchp9 原資料＋原窗（commit {P9_COMMIT} 的 archive）＋新引擎")
    if not os.path.isdir(os.path.join(P9_ARCHIVE, "data", "stocks")):
        chk("archive 存在", False, f"先跑：git archive {P9_COMMIT} backtest data/meta data/stocks data/adj | tar -x -C {P9_ARCHIVE}")
        return
    if not os.path.isdir(P9_RUN):
        os.makedirs(P9_RUN)
        subprocess.check_call(["cp", "-r", os.path.join(P9_ARCHIVE, "backtest"), P9_RUN])
        subprocess.check_call(["chmod", "-R", "u+w", P9_RUN])
        os.symlink(os.path.join(P9_ARCHIVE, "data"), os.path.join(P9_RUN, "data"))
        os.makedirs(os.path.join(P9_RUN, "backtest", "resultsp4"), exist_ok=True)
        subprocess.check_call(["cp", os.path.join(REPO, "backtest", "resultsp4", "panel.csv.gz"), os.path.join(P9_RUN, "backtest", "resultsp4")])
    subprocess.check_call(["cp", os.path.join(REPO, "backtest", "research11.py"), os.path.join(P9_RUN, "backtest", "research11.py")])
    p = subprocess.run([PY, os.path.abspath(__file__), "_gate2"], cwd=P9_RUN, capture_output=True, text=True)
    print(p.stdout[-4000:]); print(p.stderr[-3000:]) if p.returncode else None
    try:
        for r in json.load(open(os.path.join(OUT, "_gate2.json"))):
            chk(r["name"], r["ok"], r["detail"])
    except Exception as e:  # noqa: BLE001
        chk("gate2 子行程", False, repr(e))


_G = {}


def _g2one(args):
    """P9 的 _one 同一條路，只多傳擴充參數（⛔ 不改 P9 的統計）。"""
    arm, seed = args
    P9, R, S = _G["P9"], _G["R"], _G["P9"]._S
    kw = {"k1": dict(entry_tranches=1), "noop_add": dict(add_rule={"kind": "gain", "x": 1e9}),
          "mult05": dict(size_mult_by_regime={"mult": 0.5, "below": _G["below60"]})}[arm]
    s = R.simulate_mtm(S["sig"], P9.RULE, P9.N_MAIN, np.random.default_rng(seed), S["closes"], S["opens"], S["ncal"],
                       return_equity=True, report_maxw=True, **kw)
    return {"arm": arm, "seed": seed, "cagr": s["cagr"], "mdd": s["mdd"], "slot": s["slot_use"], "m": s["m"], "maxw": s["max_pos_frac"],
            "eqsha": __import__("hashlib").sha256(np.asarray(s["equity"], float).tobytes()).hexdigest()}


def _g2base(args):
    arm, seed = args
    P9, R, S = _G["P9"], _G["R"], _G["P9"]._S
    s = R.simulate_mtm(S["sig"], P9.RULE, P9.N_MAIN, np.random.default_rng(seed), S["closes"], S["opens"], S["ncal"],
                       return_equity=True, weak=(S["weak"] if arm == "b" else None), weak_size=P9.WEAK_SIZE, report_maxw=True)
    return {"arm": arm, "seed": seed, "eqsha": __import__("hashlib").sha256(np.asarray(s["equity"], float).tobytes()).hexdigest()}


def _gate2(reps=200, procs=4):
    root = os.getcwd()
    sys.path.insert(0, root)
    from multiprocessing import Pool
    from backtest import data as D, researchp9 as P9, researchp7 as P7, researchp1 as P1, p4_features as P4F, research11 as R, research13 as R13
    out = []

    def add(name, ok, detail=""):
        out.append({"name": name, "ok": bool(ok), "detail": detail}); print(("✓ " if ok else "✗ ") + name, detail, flush=True)
    add("子行程讀的是 archive 的程式與資料、引擎是新版", R.__file__.startswith(root) and D.DATA.startswith(root) and hasattr(R, "regime_below"),
        f"R={R.__file__}｜DATA={os.path.realpath(D.DATA)}")
    cal = D.load_calendar(); ncal = len(cal)
    uni = D.load_universe().set_index("stock_id")["market"]
    panel = P4F.read_panel(os.path.join(root, "backtest", "resultsp4", "panel.csv.gz"))
    closes, opens = P1.load_prices(set(panel["stock_id"]), cal, uni)
    sig = P7.build_sig_gate_b(panel, cal, closes, opens)
    want = {"rows": 2882, "stocks": 919, "months": 109, "m_min": "2017-03", "m_max": "2026-03", "e_min": 523, "e_max": 2716}
    got = {"rows": len(sig), "stocks": sig["sid"].nunique(), "months": sig["month"].nunique(), "m_min": sig["month"].min(),
           "m_max": sig["month"].max(), "e_min": int(sig["entry_pos"].min()), "e_max": int(sig["entry_pos"].max())}
    add("sig 七個驗收數與 researchp9 相同", got == want, f"{got}")
    bench = pd.Series(D.load_stock("0050", "twse", cal).df["close"].to_numpy()).ffill().to_numpy(float)
    weak = P9.weak_flags(bench, ncal)
    below60 = R.regime_below(bench, 60)
    add("weak_flags(0050)[t] ＝ regime_below(0050, 60)[t−1]（共用同一個算式）", np.array_equal(weak[1:], below60[:-1]) and not weak[0])
    first_all = int(sig["entry_pos"].min()); end_all = ncal
    split_pos = int(cal.searchsorted(pd.Timestamp(R13.SPLIT + "-01")))
    add("窗 ＝ 浮動窗 [523, 2855) ＝ 2017-03-02 ~ 2026-09-18（P9B_REPORT 基準註記）",
        (first_all, end_all) == (523, 2855) and str(cal[first_all].date()) == "2017-03-02" and str(cal[end_all - 1].date()) == "2026-09-18",
        f"[{first_all}, {end_all}) {cal[first_all].date()} ~ {cal[end_all - 1].date()}")
    _G.update(P9=P9, R=R, below60=below60)
    t0 = time.time()
    with Pool(procs, initializer=P9._init, initargs=(sig, closes, opens, ncal, first_all, split_pos, end_all, weak)) as pool:
        res = pool.map(P9._one, [(arm, P9.SEED0 + r) for arm in ("base", "b") for r in range(reps)], chunksize=4)
        ext = pool.map(_g2one, [(arm, P9.SEED0 + r) for arm in ("k1", "noop_add", "mult05") for r in range(reps)], chunksize=4)
        shas = pool.map(_g2base, [(arm, P9.SEED0 + r) for arm in ("base", "b") for r in range(reps)], chunksize=4)
    print(f"[run] {len(res) + len(ext) + len(shas)} 趟（{time.time() - t0:.0f}s）", flush=True)
    df = pd.DataFrame(res)
    ref = pd.read_csv(os.path.join(root, "backtest", "resultsp9", "seeds.csv"), float_precision="round_trip")
    cols = [c for c in ref.columns if c not in ("arm", "seed")]
    m = ref.merge(df, on=["arm", "seed"], suffixes=("_ref", "_new"), how="outer", indicator=True)
    for arm in ("base", "b"):
        g = m[m["arm"] == arm]
        diff = []
        for c in cols:
            a_, b_ = g[c + "_ref"].to_numpy(float), g[c + "_new"].to_numpy(float)
            same = (a_ == b_) | (np.isnan(a_) & np.isnan(b_))
            if not same.all():
                diff.append((c, int((~same).sum())))
        add(f"researchp9 {arm} 臂：{len(g)} 顆種子 × {len(cols)} 欄（{'、'.join(cols)}）與 resultsp9/seeds.csv 逐位元相同",
            len(g) == reps and (g["_merge"] == "both").all() and not diff, f"不同 {diff}")
    cells = pd.read_csv(os.path.join(root, "backtest", "resultsp9", "cells.csv"), float_precision="round_trip").set_index("arm")
    for arm in ("base", "b"):
        g = df[df["arm"] == arm]; md = g.median(numeric_only=True)
        vals = {"cagr": md["cagr"], "mdd": md["mdd"], "cagr_p10": g["cagr"].quantile(.1), "cagr_p90": g["cagr"].quantile(.9),
                "mdd_p10": g["mdd"].quantile(.1), "mdd_p90": g["mdd"].quantile(.9), "slot": md["slot"], "m": md["m"], "expo": md["expo"]}
        bad = {k: (v, cells.loc[arm, k]) for k, v in vals.items() if repr(float(v)) != repr(float(cells.loc[arm, k]))}
        add(f"researchp9 {arm} 臂 cells.csv 列：年化中位 {vals['cagr'] * 100:+.2f}%／回落中位 {vals['mdd'] * 100:.1f}%（＋p10/p90、槽、筆、曝險）逐位元相同",
            not bad, f"cagr={vals['cagr']!r} mdd={vals['mdd']!r}；不同 {bad}")
    E = pd.DataFrame(ext); SH = pd.DataFrame(shas).set_index(["arm", "seed"])["eqsha"]
    for arm, ref_arm, what in (("k1", "base", "entry_tranches=1"), ("noop_add", "base", "add_rule gain x=1e9（擴充路徑開著、沒觸發）"),
                               ("mult05", "b", "size_mult_by_regime(mult 0.5, regime_below(0050,60))")):
        g = E[E["arm"] == arm].set_index("seed"); r_ = df[df["arm"] == ref_arm].set_index("seed")
        ok = all(repr(float(g.loc[s_, k])) == repr(float(r_.loc[s_, k])) for s_ in g.index for k in ("cagr", "mdd", "slot", "m", "maxw"))
        ok = ok and all(g.loc[s_, "eqsha"] == SH.loc[(ref_arm, s_)] for s_ in g.index)
        add(f"{what} ⇒ 與 {ref_arm} 臂 {len(g)} 顆種子逐位元相同（equity sha＋cagr／mdd／槽／筆／maxw）", ok)
    # P7 既有結果（同一個 archive：P7 跑在 eb78ae420e，data/stocks、adj、calendar、stocks.csv 與 0dc5d62b2a 無差）
    try:
        T7, _ = P7.run_cells(sig, closes, opens, cal, bench, [None, ("fix", 0.15)], [8], reps, procs, log=lambda *a, **k: None)
        c7 = pd.read_csv(os.path.join(root, "backtest", "resultsp7", "cells.csv"), float_precision="round_trip")
        for tag in ("none", "fix 15%"):
            a_ = T7[(T7["N"] == 8) & (T7["stop"] == tag)].iloc[0]; b_ = c7[(c7["N"] == 8) & (c7["stop"] == tag)].iloc[0]
            num = [c for c in c7.columns if c in T7.columns and c not in ("N", "stop")]
            bad = [c for c in num if repr(a_[c] if not isinstance(a_[c], (np.floating, float)) else float(a_[c]))
                   != repr(b_[c] if not isinstance(b_[c], (np.floating, float)) else float(b_[c]))]
            add(f"P7 既有結果 N=8 {tag}：{len(num)} 欄與 resultsp7/cells.csv 逐位元相同（200 顆種子重跑）", not bad,
                f"年化 {float(a_['cagr']):.10f}／回落 {float(a_['mdd']):.10f}；不同 {[(c, a_[c], b_[c]) for c in bad][:4]}")
    except Exception as e:  # noqa: BLE001
        add("P7 既有結果重跑", False, repr(e))
    json.dump(out, open(os.path.join(OUT, "_gate2.json"), "w"), ensure_ascii=False, indent=1)


def nonid():
    print("── ⛔ 不是恆等輸出：真資料（tw-p17 工作樹、門檻B、H120、N=8、種子 0）；⛔ 只報「不同」與觸發次數，⛔ 不報年化／回落")
    from backtest import research11 as R
    cal, ncal, uni, panel, closes, opens, sig, bench = load_real()
    hi = {s: (pd.Series(c).rolling(120).max().to_numpy() <= c) for s, c in ((s, np.asarray(closes[s], float)) for s in set(sig["sid"]))}
    CFG = {"2-A k=2": dict(entry_tranches=2), "2-A k=3": dict(entry_tranches=3),
           "2-B ⓐ gain 15%": dict(add_rule={"kind": "gain", "x": 0.15}),
           "2-B ⓑ flag（測試用旗標＝收盤創 120 日新高；⛔ 不是 PREREGP8 三分位）": dict(add_rule={"kind": "flag", "flags": hi}),
           "2-B ⓒ hold 40": dict(add_rule={"kind": "hold", "days": 40}),
           "2-C ⓐ trim −10%": dict(trim_rule={"x": 0.10, "frac": 0.5}),
           "2-C ⓒ MA60 ×1.5": dict(size_mult_by_regime={"mult": 1.5, "ma": 60, "bench": bench}),
           "2-C ⓓ MA20 ×0.5": dict(size_mult_by_regime={"mult": 0.5, "ma": 20, "bench": bench}),
           "2-C ⓔ MA10 ×0.5": dict(size_mult_by_regime={"mult": 0.5, "ma": 10, "bench": bench}),
           "2-C ⓕ MA60 賣半": dict(regime_trim={"hold": 0.5, "ma": 60, "bench": bench}),
           "2-C ⓖ MA20 賣半": dict(regime_trim={"hold": 0.5, "ma": 20, "bench": bench}),
           "2-C ⓗ MA10 賣半": dict(regime_trim={"hold": 0.5, "ma": 10, "bench": bench})}
    trig = {"2-A": "x_tr_buys", "2-B": "x_add_n", "2-C ⓐ": "x_trim_n", "2-C ⓒ": "x_mult_n", "2-C ⓓ": "x_mult_n", "2-C ⓔ": "x_mult_n",
            "2-C ⓕ": "x_rt_sell_n", "2-C ⓖ": "x_rt_sell_n", "2-C ⓗ": "x_rt_sell_n"}
    off = R.simulate_mtm(sig, "H120", 8, np.random.default_rng(0), closes, opens, ncal, return_equity=True)
    for nm, kw in CFG.items():
        o = R.simulate_mtm(sig, "H120", 8, np.random.default_rng(0), closes, opens, ncal, return_equity=True, **kw)
        key = next(v for k, v in trig.items() if nm.startswith(k))
        diff = o["equity"].tobytes() != off["equity"].tobytes()
        extra = {k: o[k] for k in o if k.startswith("x_") and k not in ("x_cost_days",) and isinstance(o[k], (int, float)) and o[k]}
        chk(f"{nm}：與全關不同、觸發 {key}={o[key]}", diff and o[key] > 0, json.dumps({k: (round(v, 4) if isinstance(v, float) else v)
                                                                                        for k, v in extra.items()}, ensure_ascii=False))


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "all"
    if mode == "_afc":
        _afc(); sys.exit(0)
    if mode == "_gate2":
        _gate2(); sys.exit(0)
    sys.path.insert(0, REPO); os.chdir(REPO)
    t0 = time.time(); fails = 0
    for m_, fn in (("fixtures", fixtures), ("gate1", gate1), ("gate2", gate2), ("nonid", nonid)):
        if mode in (m_, "all"):
            RESULTS.clear(); fn(); dump(m_); fails += sum(not r["ok"] for r in RESULTS)
    print(f"完成（{time.time() - t0:.0f}s）")
    sys.exit(1 if fails else 0)

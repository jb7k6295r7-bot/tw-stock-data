# -*- coding: utf-8 -*-
"""researchGranville2（葛蘭碧 seq2 拆件）自測（合成 fixture；⛔ 不讀任何報酬）——回測線計算子代理。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchGranville2_check
涵蓋：A0 ＝ seq1 seg_features（多組 fixture＋隨機漫步＋壞根切段）；各版拿掉的條件（方向、前置位置、只剩觸發）各有 fixture；
      A0 ⊆ A1、A2 ⊆ A3；買2「跌破」須有前一根線上（★S4）；停損價各版同定義；B1／B2／B3 出場邏輯；同根取較低（seq373）於 B1、B2；
      壞根、下市於 B3；ret_one（正式用）合成價對帳；結果句固定語與禁語；閘門（正式跑只認 seq487）；seq1 程式未改；
      已產出檔：A0、B0 重現 seq1 事件檔（逐字）、無報酬欄、描述欄乾跑只寫 filled／EMPTY。
"""
from __future__ import annotations

import glob
import io
import os
import subprocess
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
from backtest import researchGranville2 as G2   # noqa: E402
from backtest import researchGranville as G     # noqa: E402

RES = []


def ok(name, cond, info=""):
    RES.append((name, bool(cond)))
    print(("PASS " if cond else "FAIL ") + name + (f"｜{info}" if info and not cond else ""), flush=True)


def V_of(c, h=None, l=None):
    h = c if h is None else h; l = c if l is None else l
    V, S, F = G2.seg_variants(c, h, l)
    return V, S, F


def vers_at(V, cell, k):
    return [v for v in G2.AV if V[(cell, v)][k]]


# ── A0 ＝ seq1 ──────────────────────────────────────────────
def t_a0_equiv():
    rng = np.random.default_rng(11)
    bad_ = 0; tot = 0
    for s in range(12):
        n = 1500
        c = np.exp(np.cumsum(rng.normal(0.0003, 0.025, n))) * 40
        h = c * (1 + np.abs(rng.normal(0, 0.01, n))); l = c * (1 - np.abs(rng.normal(0, 0.015, n)))
        try:
            V, S, F = G2.seg_variants(c, h, l, check=True)
        except SystemExit:
            bad_ += 1; continue
        tot += sum(int(V[(cell, "A0")].sum()) for cell in G2.BUY)
        for cell in G2.BUY:
            if (V[(cell, "A0")] & ~V[(cell, "A1")]).any() or (V[(cell, "A0")] & ~V[(cell, "A2")]).any() \
                    or (V[(cell, "A1")] & ~V[(cell, "A3")]).any() or (V[(cell, "A2")] & ~V[(cell, "A3")]).any():
                bad_ += 1
    ok("A0 ＝ seq1 seg_features（12 條隨機漫步，含停損價）且 A0 ⊆ A1、A2 ⊆ A3", bad_ == 0 and tot > 0, f"bad={bad_} tot={tot}")
    # 壞根切段
    c = np.exp(np.cumsum(rng.normal(0.0003, 0.025, 1500))) * 40
    bad = np.zeros(1500, bool); bad[[400, 900]] = True
    V, S, X5, MA = G2.stock_variants(c, c, c * 0.99, bad)
    F = G.stock_features(c, c, c * 0.99, bad)
    ok("壞根切段後 A0 ＝ seq1 stock_features、X5 相同", all(np.array_equal(V[(cell, "A0")], F[bk]) for cell, bk in (("買1", "B1"), ("買2", "B2"), ("買3", "B3")))
       and np.array_equal(X5, F["X5"]) and np.array_equal(MA, F["MA"], equal_nan=True))


# ── 買1 ──────────────────────────────────────────────
def t_buy1():
    pat = np.array([4.0] * 14 + [16.0] * 6)
    c = np.tile(pat, 15)                                   # seq1 fixture：MA 走平、274 為轉折
    V, S, F = V_of(c)
    ok("買1 走平：四版皆成立", vers_at(V, "買1", 274) == ["A0", "A1", "A2", "A3"])
    dn = c - np.arange(300) / 64.0                         # 下彎
    V, S, F = V_of(dn)
    ok("買1 下彎：A0／A2 不成立、A1／A3 成立（方向條件被拿掉）", F["down"][274] and vers_at(V, "買1", 274) == ["A1", "A3"])
    c3 = c.copy(); c3[[220, 221, 222]] = 8.0                # 前 60 日 < MA 只 39 日
    V, S, F = V_of(c3)
    ok("買1 前 60 日 < MA 39 日：A0／A1 不成立、A2／A3 成立（前置位置被拿掉）", vers_at(V, "買1", 274) == ["A2", "A3"])
    found = None
    for mm in range(1, 14):                                # 下彎版：把 220 起 mm 個低點拉到 8，直到前 60 日 < MA 少於 40 日
        d3 = dn.copy(); d3[220:220 + mm] = 8.0
        Fm = G.seg_features(d3, d3, d3)
        cnt = int(np.sum(d3[214:274] < Fm["MA"][214:274]))
        if cnt < 40 and d3[273] <= Fm["MA"][273] and d3[274] > Fm["MA"][274]:
            found = (mm, cnt); break
    V, S, F = V_of(d3)
    ok("買1 下彎且前 60 日 < MA 不足 40 日：只剩 A3", found is not None and F["down"][274] and vers_at(V, "買1", 274) == ["A3"], str(found))
    ok("買1 停損價各版同 ＝ 前 60 日最低收盤", S["買1"][274] == np.min(d3[214:274]))
    up = np.full(300, 64.0) + np.arange(300) / 4.0         # 收盤恆在線上 ⇒ 沒有觸發
    V, S, F = V_of(up)
    ok("買1 沒有「≤ 轉 >」⇒ A3 也不成立", not V[("買1", "A3")].any())


# ── 買2 ──────────────────────────────────────────────
def t_buy2():
    c = G2_mk_up(300, 260, 4)
    V, S, F = V_of(c)
    ok("買2 原版 fixture：四版皆成立、停損 32", vers_at(V, "買2", 264) == ["A0", "A1", "A2", "A3"] and S["買2"][264] == 32.0)
    c = G2_mk_steep(320, 260, 11)
    V, S, F = V_of(c)
    ok("買2 跌破 11 日（MA 仍上揚）：A0／A1 不成立、A2／A3 成立（k ≤ 10 被拿掉）",
       F["MA"][271] > F["MA"][251] and vers_at(V, "買2", 271) == ["A2", "A3"] and S["買2"][271] == 32.0, str(vers_at(V, "買2", 271)))
    c = G2_mk_steep(320, 260, 30)
    V, S, F = V_of(c)
    ok("買2 跌破 30 日（MA 仍上揚）：只 A2／A3、停損 ＝ 跌破期間最低",
       F["MA"][290] > F["MA"][270] and vers_at(V, "買2", 290) == ["A2", "A3"] and S["買2"][290] == 32.0, str(vers_at(V, "買2", 290)))
    c = G2_mk_steep(320, 260, 10)
    V, S, F = V_of(c)
    ok("買2 跌破 10 日（k＝10 邊界）：四版皆成立", vers_at(V, "買2", 270) == ["A0", "A1", "A2", "A3"])
    c = G2_mk_up(300, 260, 4); c[250] = 32.0               # 跌破前 20 日內有一天線下
    V, S, F = V_of(c)
    ok("買2 跌破前 20 日不全在線上：A2／A3 成立", vers_at(V, "買2", 264) == ["A2", "A3"])
    # 方向：MA 下彎、跌破前 20 日都在線上、k＝4
    c = np.full(400, 64.0); c[:150] = 400.0; c[300:340] = 120.0; c[340:344] = 30.0; c[344:] = 120.0
    V, S, F = V_of(c)
    k = 344
    pre = all(c[j] > F["MA"][j] for j in range(320, 340)) and all(c[j] <= F["MA"][j] for j in range(340, 344)) and c[k] > F["MA"][k]
    ok("買2 MA200 下彎（其餘原版條件都成立）：A0／A2 不成立、A1／A3 成立", pre and F["down"][k] and vers_at(V, "買2", k) == ["A1", "A3"],
       f"pre={pre} down={F['down'][k]} vers={vers_at(V, '買2', k)}")
    # ★S4：線下段從 MA 剛可算的第一根開始（沒有「由上往下」）⇒ A3 也不成立
    c = 64.0 - np.arange(400) / 4.0; c[240] = 400.0
    V, S, F = V_of(c)
    ok("買2 ★S4 跌破須有前一根線上：線下從 MA 起算第一根開始 ⇒ A3 不成立", F["J2"][240] and c[240] > F["MA"][240] and not V[("買2", "A3")][240])
    c2 = c.copy(); c2[205] = 400.0                          # 讓 205 線上 ⇒ 206 起才是跌破
    V, S, F = V_of(c2)
    ok("買2 ★S4 有前一根線上 ⇒ A3／A2 依方向成立（下彎 ⇒ 只 A3）", V[("買2", "A3")][240] and not V[("買2", "A2")][240] and S["買2"][240] == np.min(c2[206:240]))


def G2_mk_up(n, dip_at, dip_len):
    c = 64.0 + np.arange(n) / 4.0
    c[dip_at:dip_at + dip_len] = 32.0
    return c


def G2_mk_steep(n, dip_at, dip_len):
    """前 150 根平 10、之後每根 +2 ⇒ 跌破期間被移出窗的是 10，MA 仍上揚。"""
    k = np.arange(n, dtype=float)
    c = np.where(k < 150, 10.0, 10.0 + 2.0 * (k - 150))
    c[dip_at:dip_at + dip_len] = 32.0
    return c


# ── 買3 ──────────────────────────────────────────────
def t_buy3():
    c = 64.0 + np.arange(300) / 4.0
    k = 280
    m = G.seg_features(c, c, c)["MA"][k]
    l = c.copy(); l[k] = m * 1.02
    V, S, F = V_of(c, c, l)
    ok("買3 原版（含等號）：四版皆成立、停損 ＝ 當天最低", vers_at(V, "買3", k) == ["A0", "A1", "A2", "A3"] and S["買3"][k] == l[k])
    c3 = c.copy(); c3[270] = 32.0
    l3 = c3.copy(); l3[k] = G.seg_features(c3, c3, c3)["MA"][k] * 1.01
    V, S, F = V_of(c3, c3, l3)
    ok("買3 前 20 日有一天線下：A2／A3 成立", vers_at(V, "買3", k) == ["A2", "A3"])
    c = np.full(400, 64.0); c[:180] = 400.0; c[300:] = 200.0
    V0, _, F0 = V_of(c)
    k = 360; l = c.copy(); l[k] = F0["MA"][k] * 1.01
    V, S, F = V_of(c, c, l)
    pre = all(c[j] > F["MA"][j] for j in range(340, 360))
    ok("買3 MA200 下彎（前 20 日在線上）：A1／A3 成立", pre and F["down"][k] and c[k] > F["MA"][k] and vers_at(V, "買3", k) == ["A1", "A3"],
       f"pre={pre} down={F['down'][k]} vers={vers_at(V, '買3', k)}")
    l2 = c.copy(); l2[k] = F0["MA"][k] * 1.03
    V, S, F = V_of(c, c, l2)
    ok("買3 最低 > MA×1.02 ⇒ A3 也不成立（觸發還在）", not V[("買3", "A3")][k])


# ── 出場 B1／B2／B3 ──────────────────────────────────────────────
def base_path(n=400, v=100.0):
    return np.full(n, v), np.full(n, v), np.zeros(n, bool), np.zeros(n, bool)


def t_exit():
    e, S = 10, 90.0; cap = e + 250; cend = 399
    c, o, x5, bad = base_path(); x5[e + 3] = True; c[e + 8] = 88.0
    X0 = G2.exit_v(c, o, x5, bad, e, S, cap, cend, 399, "SX")
    X1 = G2.exit_v(c, o, x5, bad, e, S, cap, cend, 399, "S")
    X2 = G2.exit_v(c, o, x5, bad, e, S, cap, cend, 399, "X")
    X3 = G2.exit_v(c, o, x5, bad, e, S, cap, cend, 399, "")
    ok("B0 ＝ seq1 exit_sim（賣5 先到 e+4）", X0 == G.exit_sim(c, o, x5, bad, e, S, cap, cend, 399) and X0["x"] == e + 4 and X0["reason"] == "賣5先到")
    ok("B1 只停損：不理賣5 ⇒ 停損 e+8 觸發、e+9 開盤", X1["x"] == e + 9 and X1["reason"] == "停損先到" and X1["kind"] == "open")
    ok("B2 只賣5：e+4 開盤", X2["x"] == e + 4 and X2["reason"] == "賣5先到")
    ok("B3 都不用：固定 e+250 收盤", X3["x"] == cap and X3["reason"] == "固定250日" and X3["kind"] == "close")
    c, o, x5, bad = base_path(); c[e + 5] = 88.0; x5[e + 20] = True
    X2 = G2.exit_v(c, o, x5, bad, e, S, cap, cend, 399, "X")
    ok("B2 不理停損：停損 e+5 不觸發、賣5 e+20 ⇒ e+21", X2["x"] == e + 21 and X2["reason"] == "賣5先到")
    c, o, x5, bad = base_path(); x5[e + 3] = True; c[e + 3] = 88.0
    ok("B1、B2 同一根兩者 ⇒ 各自只報自己的臂", G2.exit_v(c, o, x5, bad, e, S, cap, cend, 399, "S")["reason"] == "停損先到"
       and G2.exit_v(c, o, x5, bad, e, S, cap, cend, 399, "X")["reason"] == "賣5先到")
    # seq373 同根取較低：B1（停損於 cap−1 觸發）、B2（賣5 於 cap−1 觸發）
    for arm, lab in (("S", "B1"), ("X", "B2")):
        c, o, x5, bad = base_path(); o[cap] = 96.0; c[cap] = 120.0
        if arm == "S":
            c[cap - 1] = 80.0
        else:
            x5[cap - 1] = True
        X = G2.exit_v(c, o, x5, bad, e, S, cap, cend, 399, arm)
        p, _ = G.exit_price(c, o, bad, e, X["x"], X["kind"], cend, 399)
        ok(f"{lab} 觸發在 cap−1 ⇒ 賣出根＝cap ⇒ 取開盤與收盤較低（seq373）", X["kind"] == "minoc" and X["x"] == cap and p == 96.0)
    c, o, x5, bad = base_path(); bad[e + 30] = True; c[e + 5] = 50.0; x5[e + 6] = True
    X = G2.exit_v(c, o, x5, bad, e, S, cap, cend, 399, "")
    ok("B3 遇壞根 ⇒ 壞根前強制出（不理觸發）", X["reason"] == "壞根前強制出" and X["x"] == e + 29)
    c, o, x5, bad = base_path(); c[e + 41:] = np.nan; o[e + 41:] = np.nan
    X = G2.exit_v(c, o, x5, bad, e, S, cap, cend, e + 40, "")
    ok("B3 下市 ⇒ 末根收盤", X["reason"] == "下市末根" and X["x"] == e + 40)
    c, o, x5, bad = base_path(); c[cap] = np.nan; o[cap] = np.nan
    X = G2.exit_v(c, o, x5, bad, e, S, cap, cend, 399, "")
    ok("B3 上限根沒成交 ⇒ 上限根以前最後有效收盤", X["x"] == cap - 1 and X["reason"] == "固定250日")


def t_ret_one():
    NC = 400
    C = np.full((3, NC), 100.0); O = np.full((3, NC), 100.0); BAD = np.zeros((3, NC), bool); LV = np.array([399, 399, 399])
    C[0, 50] = 110.0; C[1, 50] = 105.0; C[2, 50] = 95.0
    a, b = G2.ret_one(C, O, BAD, LV, 399, 0, [1, 2], 10, 50, "close", 0.00585)
    ok("ret_one 合成價：訊號 110/100−1−成本、對照平均（105、95）", abs(a - (0.10 - 0.00585)) < 1e-12 and abs(b - (0.0 - 0.00585)) < 1e-12)
    O[0, 50] = 99.0
    a, _ = G2.ret_one(C, O, BAD, LV, 399, 0, [1], 10, 50, "minoc", 0.0)
    ok("ret_one minoc ＝ min(開, 收)", abs(a - (99.0 / 100 - 1)) < 1e-12)


# ── 結果句、閘門、seq1 程式未改 ──────────────────────────────────────────────
def t_sentence_gate():
    rows = {nm: {"n": 100, "months": 30, "mean": 0.0, "median": 0.0, "mean_ex_max1": 0.0, "lo": 0.0, "hi": 0.0, "停損先到": 0.5, "賣5先到": 0.2, "持有中位": 7.0}
            for nm in ("探索", "確認")}
    s = G2.result_sentence("買2", "B3", rows, dry=True)
    ok("結果句 必附「拆件是看過 seq1 結果後追加的，只描述」", G2.PHRASE in s and "拆件是看過 seq1 結果後追加的，只描述" in s)
    ok("結果句 乾跑不填報酬（不出現 % 的超額值）", "乾跑不填" in s and "平均 +" not in s)
    rows["確認"]["months"] = 20
    s2 = G2.result_sentence("買1", "A1", rows, dry=False)
    ok("結果句 n_eff < 24 加註、正式版填平均／中位／去掉最大 1 筆／CI", "（< 24，只描述、樣本不足）" in s2 and "去掉最大 1 筆" in s2 and "99% CI" in s2)
    ok("結果句 不含判定措辭（通過／測不出／還沒測）", not any(w in s + s2 for w in ("通過", "測不出", "還沒測")))
    old = G2.VNAME["A1"]
    try:
        G2.VNAME["A1"] = "反向顯著"
        G2.result_sentence("買1", "A1", rows, dry=True); raised = False
    except ValueError:
        raised = True
    finally:
        G2.VNAME["A1"] = old
    ok("結果句 若含禁語 ⇒ 擋下（突變）", raised)
    g = G2.gate
    ok("閘門 無參數 ⇒ 拒跑", g([])[0] == "refuse")
    ok("閘門 --formal 無 ruling ⇒ 拒跑", g(["--formal"])[0] == "refuse")
    ok("閘門 --formal --ruling seq485（seq1 的號）⇒ 拒跑", g(["--formal", "--ruling", "seq485"])[0] == "refuse")
    ok("閘門 --formal --ruling seq486 ⇒ 拒跑", g(["--formal", "--ruling", "seq486"])[0] == "refuse")
    ok("閘門 --formal --ruling seq487 ⇒ 正式", g(["--formal", "--ruling", "seq487"])[0] == "formal")
    ok("閘門 --formal --dry ⇒ 拒跑", g(["--formal", "--dry", "--ruling", "seq487"])[0] == "refuse")
    ok("閘門 --formal --limit ⇒ 拒跑", g(["--formal", "--ruling", "seq487", "--limit", "5"])[0] == "refuse")
    ok("閘門 --dry ⇒ 乾跑", g(["--dry"])[0] == "dry")
    ok("閘門 未知參數 ⇒ 拒跑", g(["--dry", "--xyz"])[0] == "refuse")
    d = subprocess.run(["git", "diff", "--quiet", "48c8bcb982", "--", "backtest/researchGranville.py", "backtest/researchGranville_check.py"],
                       cwd=os.path.expanduser("~/tw-p17")).returncode
    ok("seq1 程式與自測與 48c8bcb982 相同（未改）", d == 0)
    ok("G2 不改 seq1 常數（CAP 250、SEED、COST、NEFF_MIN 24）", G.CAP == 250 and G.SEED == 20261028 and G.COST == 0.00585 and G.NEFF_MIN == 24)


# ── 已產出檔 ──────────────────────────────────────────────
def t_outputs():
    od = os.path.join(G2.OUT, "freq")
    if not os.path.isdir(od) or not os.path.exists(os.path.join(od, "freq.json")):
        ok("產出檔（尚未產出，略）", True); return
    forbid = ("報酬", "超額", "勝率", "R_", "ret", "price", "價")
    bad = []
    for f in glob.glob(os.path.join(od, "events_*.csv.gz")) + [os.path.join(od, x) for x in ("freq_versions.csv", "exit_reasons.csv", "hold_dist.csv", "overlap_vs_A0.csv")]:
        cols = pd.read_csv(f, nrows=0).columns
        bad += [f"{os.path.basename(f)}:{c}" for c in cols if any(k in c for k in forbid)]
    ok("產出 events／頻率表無報酬／價格欄", not bad, str(bad[:5]))
    ds = pd.read_csv(os.path.join(od, "desc_dryrun_status.csv"))
    ok("產出 描述欄乾跑檔只有 filled／EMPTY（不寫值）", set(ds.columns) == {"section", "cell", "stat", "n", "status"} and set(ds["status"]) <= {"filled", "EMPTY"})
    # A0、B0 ＝ seq1 事件檔（逐字；另讀一次檔案比）
    allsame = True; info = []
    for cell in G2.BUY:
        ref = pd.read_csv(os.path.join(G2.SEQ1_FREQ, f"events_{cell}.csv.gz"), dtype=str, keep_default_na=False)
        for v in ("A0", "B0"):
            me = pd.read_csv(os.path.join(od, f"events_{cell}_{v}.csv.gz"), dtype=str, keep_default_na=False)
            same = list(ref.columns) == list(me.columns) and ref.shape == me.shape and bool((ref.values == me.values).all())
            allsame &= same; info.append(f"{cell}{v}:{same}")
    ok("產出 A0、B0 事件、對照、出場日 ＝ seq1 freq 事件檔（逐字）", allsame, str(info))
    # B 組事件、對照 ＝ A0（只出場欄不同）
    same_entry = True
    for cell in G2.BUY:
        a0 = pd.read_csv(os.path.join(od, f"events_{cell}_A0.csv.gz"), dtype=str, keep_default_na=False)
        for v in ("B1", "B2", "B3"):
            b = pd.read_csv(os.path.join(od, f"events_{cell}_{v}.csv.gz"), dtype=str, keep_default_na=False)
            cols = [c for c in a0.columns if c not in ("出場日", "出場方式", "出場原因", "旗標", "持有天數", "對照出場狀態")]
            same_entry &= a0[cols].equals(b[cols])
            if v == "B1":
                same_entry &= not b["出場原因"].str.startswith(("賣5先到", "同日兩者")).any()
            if v == "B2":
                same_entry &= not b["出場原因"].str.startswith(("停損先到", "同日兩者")).any()
            if v == "B3":
                same_entry &= set(b.loc[b["出場原因"] != "", "出場原因"]) <= {"固定250日", "壞根前強制出", "下市末根"}
    ok("產出 B1～B3 事件與對照 ＝ A0；B1 無賣5、B2 無停損、B3 只有固定／壞根／下市", same_entry)
    ov = pd.read_csv(os.path.join(od, "overlap_vs_A0.csv"))
    ok("產出 A0 原始訊號 ⊆ 各版原始訊號（A0原始不在本版 ＝ 0）", (ov["A0原始不在本版(應為0)"] == 0).all())
    ok("產出 結果句樣板每版都附固定語", all(G2.PHRASE in s for s in open(os.path.join(od, "result_sentence_template.txt"), encoding="utf-8").read().strip().split("\n\n")))


def main():
    for f in (t_a0_equiv, t_buy1, t_buy2, t_buy3, t_exit, t_ret_one, t_sentence_gate, t_outputs):
        f()
    n = len(RES); p = sum(1 for _, x in RES if x)
    print(f"\n自測 {p}/{n} 通過")
    sys.exit(0 if p == n else 1)


if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
"""researchGranville2（葛蘭碧 seq2 拆件）自測（合成 fixture；⛔ 不讀任何報酬）——回測線計算子代理。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchGranville2_check
涵蓋：A0 ＝ seq1 seg_features（多組 fixture＋隨機漫步＋壞根切段）；各版拿掉的條件（方向、前置位置、只剩觸發）各有 fixture；
      A0 ⊆ A1、A2 ⊆ A3；買2「跌破」須有前一根線上（★S4）；停損價各版同定義；B1／B2／B3 出場邏輯；同根取較低（seq373）於 B1、B2；
      壞根、下市於 B3；ret_one（正式用）合成價對帳；結果句固定語與禁語；閘門（正式跑只認 seq487）；seq1 程式未改；
      已產出檔：A0、B0 重現 seq1 事件檔（逐字）、無報酬欄、描述欄乾跑只寫 filled／EMPTY。
沿革：裁定 seq490／seq492（登錄 seq3）⇒ 固定句換新（舊句不可再出現）、Bonferroni 18 格 99.72% CI 與 99% CI 並列、★ 註一行、--relabel 閘門；
      正式輸出對 b5bc39f2cd：舊數字逐位元相同、結果句去新片段後逐字相同、99.72% CI 由原 main_excess 獨立重算相符。
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
NEW_PHRASE = "拆法在看任何報酬前、照使用者要求定好（10/29 04:24）。用途是看效果來自哪一部分。"   # 裁定 seq490 逐字
OLD_PHRASE = "拆件是看過 seq1 結果後追加的，只描述"                                                  # seq487（已更正）


def t_sentence_gate():
    rows = {nm: {"n": 100, "months": 30, "mean": 0.0, "median": 0.0, "mean_ex_max1": 0.0, "lo": -0.01, "hi": 0.02, "lo95": -0.005, "hi95": 0.015,
                 "loB": -0.02, "hiB": 0.03, "停損先到": 0.5, "賣5先到": 0.2, "持有中位": 7.0}
            for nm in ("探索", "確認")}
    s = G2.result_sentence("買2", "B3", rows, dry=True)
    ok("固定句 ＝ 裁定 seq490 逐字", G2.PHRASE == NEW_PHRASE and G2.PHRASE_SEQ487 == OLD_PHRASE)
    ok("結果句 必附 seq490 新固定句、⛔ 不含 seq487 舊句", s.endswith(NEW_PHRASE) and OLD_PHRASE not in s)
    ok("結果句 乾跑不填報酬（不出現 % 的超額值）", "乾跑不填" in s and "平均 +" not in s)
    rows["確認"]["months"] = 20
    s2 = G2.result_sentence("買1", "A1", rows, dry=False)
    ok("結果句 n_eff < 24 加註、正式版填平均／中位／去掉最大 1 筆／CI", "（< 24，只描述、樣本不足）" in s2 and "去掉最大 1 筆" in s2 and "99% CI" in s2)
    ok("結果句 99% CI 與 Bonferroni 18 格 99.72% CI 並列（確認段 18 格本體不加範圍註）",
       "月分群 99% CI [-1.00%, +2.00%]、Bonferroni 18 格 99.72% CI [-2.00%, +3.00%]；另一讀法 95% CI" in s2
       and "Bonferroni 18 格 99.72% CI（探索段只描述） [-2.00%, +3.00%]" in s2 and s2.count("99.72% CI") == s2.count("月分群 99% CI") == 2)
    s3 = G2.result_sentence("買2", "B0", rows, dry=False)
    ok("結果句 A0／B0 的 99.72% CI 標「不在 18 格內，只參考」", "99.72% CI（A0／B0 不在 18 格內，只參考） [" in s3)
    ok("Bonferroni 18 格：alpha ＝ 0.05/18、18 格 ＝ 3 買點 × A1～A3、B1～B3", abs(G2.BONF_ALPHA - 0.05 / 18) < 1e-15 and len(G2.BONF_CELLS) == 18
       and set(G2.BONF_CELLS) == {(c, v) for c in ("買1", "買2", "買3") for v in ("A1", "A2", "A3", "B1", "B2", "B3")})
    xx = np.random.default_rng(3).normal(0.01, 0.1, 600); mm = np.repeat(np.arange(120), 5)
    b = G2.bonf_ci(xx, mm); c99 = G.cluster_boot(xx, mm); ref = G.cluster_boot(xx, mm, alpha=0.05 / 18)
    ok("bonf_ci ＝ seq1 cluster_boot（同 nboot、seed），只換 alpha；區間包住 99%", b == ref and b["lo"] < c99["lo"] and b["hi"] > c99["hi"])
    hl = G2.head_lines()
    ok("開頭照記：★S4、★S6、★S8、★S9 一行、不判定不加 N 一行、多重比較一行，每行附新固定句",
       sum("★S4、★S6、★S8、★S9" in x for x in hl) == 1 and any("不加 N" in x for x in hl) and any("99.72%" in x for x in hl)
       and all(x.endswith(NEW_PHRASE) for x in hl))
    ok("結果句 不含判定措辭（通過／測不出／還沒測）", not any(w in s + s2 + s3 + "".join(hl) for w in ("通過", "測不出", "還沒測")))
    try:
        G2.guard("買2｜B2；" + OLD_PHRASE + "。"); raised_old = False
    except ValueError:
        raised_old = True
    ok("擋門：舊固定句再出現 ⇒ 擋下（突變）", raised_old)
    try:
        G2.guard("買2｜B2 通過"); raised_v = False
    except ValueError:
        raised_v = True
    ok("擋門：「通過」⇒ 擋下（突變）", raised_v)
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
    ok("閘門 --relabel --ruling seq490 ⇒ 標籤更正", g(["--relabel", "--ruling", "seq490"])[0] == "relabel")
    ok("閘門 --relabel 無 ruling／seq487／seq492 ⇒ 拒跑", all(g(x)[0] == "refuse" for x in
       (["--relabel"], ["--relabel", "--ruling", "seq487"], ["--relabel", "--ruling", "seq492"])))
    ok("閘門 --relabel 夾 --formal／--dry／--procs ⇒ 拒跑", all(g(x)[0] == "refuse" for x in
       (["--relabel", "--formal", "--ruling", "seq490"], ["--relabel", "--dry", "--ruling", "seq490"], ["--relabel", "--ruling", "seq490", "--procs", "2"])))
    ok("閘門 --formal --ruling seq487 預設 procs 3", g(["--formal", "--ruling", "seq487"]) == ("formal", 3, None))
    src = open(os.path.join(os.path.expanduser("~/tw-p17"), "backtest/researchGranville2.py"), encoding="utf-8").read()
    hdr = src.split('"""')[1]
    ok("程式開頭有沿革行（引 seq490、seq492、登錄 seq3 sha）", "沿革：" in hdr and "seq490" in hdr and "seq492" in hdr and "1fc4dda730b513ac" in hdr)
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
    # freq/ 是 seq490 之前的乾跑歷史檔（無報酬），不改：樣板仍是當時的 seq487 句
    ok("產出（乾跑歷史檔）結果句樣板每版都附當時固定語（seq487，未改寫）",
       all(G2.PHRASE_SEQ487 in s for s in open(os.path.join(od, "result_sentence_template.txt"), encoding="utf-8").read().strip().split("\n\n")))


# ── 正式輸出：標籤更正（seq490／seq492）後 ──────────────────────────────────────────────
def _show(path):
    return subprocess.run(["git", "show", f"{G2.BASE_COMMIT}:{path}"], cwd=os.path.expanduser("~/tw-p17"), capture_output=True, check=True).stdout


def _leaves(o, p=()):
    if isinstance(o, dict):
        for k, v in o.items():
            yield from _leaves(v, p + (k,))
    elif isinstance(o, list):
        for k, v in enumerate(o):
            yield from _leaves(v, p + (k,))
    else:
        yield p, o


def t_formal():
    import json, re
    od = os.path.join(G2.OUT, "formal")
    root = os.path.expanduser("~/tw-p17")
    if not os.path.exists(os.path.join(root, od, "formal.json")):
        ok("正式輸出（尚未產出，略）", True); return
    J = json.load(open(os.path.join(root, od, "formal.json"), encoding="utf-8"))
    J0 = json.loads(_show(f"{od}/formal.json").decode("utf-8"))
    # 1. 既有鍵值：數字、布林逐位元相同；字串只有 NOTES 的舊固定句那條與結果句改
    L0 = dict(_leaves(J0)); L1 = dict(_leaves(J))
    miss = [p for p in L0 if p not in L1]
    numdiff = [p for p, v in L0.items() if p in L1 and not isinstance(v, str) and (type(v) is not type(L1[p]) or v != L1[p])]
    strdiff = [p for p, v in L0.items() if p in L1 and isinstance(v, str) and v != L1[p]]
    ok("formal.json 舊有鍵全在、數字／布林全同（對 b5bc39f2cd）", not miss and not numdiff and sum(1 for v in L0.values() if not isinstance(v, str)) > 100,
       f"miss={miss[:3]} numdiff={numdiff[:3]}")
    ok("formal.json 改動的舊字串只限 NOTES 舊句那條與 24 句結果句", all(p[0] in ("NOTES", "結果句") for p in strdiff) and len(strdiff) == 1 + 24, str(strdiff[:4]))
    strip = re.compile("、" + re.escape(G2.BONF_LAB) + r"(（[^）]*）)? \[[^\]]*\]")
    back = {k: strip.sub("", s).replace("；" + NEW_PHRASE, "；" + OLD_PHRASE + "。") for k, s in J["結果句"].items()}
    ok("formal.json 結果句：去掉 99.72% CI、換回舊句 ⇒ 與 b5bc39f2cd 逐字相同（數字未變）", back == J0["結果句"])
    ok("formal.json NOTES 新句、無舊句；沿革引 seq490、seq492；登錄 seq3 9973 B", any(NEW_PHRASE in x for x in J["NOTES"])
       and not any(OLD_PHRASE in x for x in J["NOTES"]) and "seq490" in J["沿革"] and "seq492" in J["沿革"]
       and J["標籤裁定"] == ["seq490", "seq492"] and J["登錄seq3"]["bytes"] == 9973)
    # 2. desc.csv：舊 11 欄原字串相同；新欄只在 99%CI 列
    D0 = pd.read_csv(io.BytesIO(_show(f"{od}/desc.csv")), dtype=str, keep_default_na=False, encoding="utf-8-sig")
    D = pd.read_csv(os.path.join(root, od, "desc.csv"), dtype=str, keep_default_na=False, encoding="utf-8-sig")
    ok("desc.csv 舊 11 欄逐字相同、新欄 lo_bonf18／hi_bonf18／bonf18_scope 接在後面",
       list(D.columns) == list(D0.columns) + ["lo_bonf18", "hi_bonf18", "bonf18_scope"] and D[list(D0.columns)].equals(D0))
    is99 = D["stat"].str.endswith("｜超額 月分群99%CI")
    ok("desc.csv 每個 99%CI 列都有 Bonferroni 18 格 CI（48 列）、其他列空", int(is99.sum()) == 48 and (D.loc[is99, "lo_bonf18"] != "").all()
       and (D.loc[is99, "hi_bonf18"] != "").all() and (D.loc[~is99, ["lo_bonf18", "hi_bonf18", "bonf18_scope"]] == "").all().all())
    q = D[is99]
    ok("desc.csv 99.72% CI 包住 99% CI", (q["lo_bonf18"].astype(float) <= q["lo"].astype(float)).all()
       and (q["hi_bonf18"].astype(float) >= q["hi"].astype(float)).all())
    core = q[q["bonf18_scope"] == "確認段 18 格之一"]
    ok("desc.csv 18 格範圍標記：確認段 A1～A3、B1～B3 共 18 列",
       len(core) == 18 and set(zip(core["cell"], core["stat"].str[:2])) == {(c + v, "確認") for c, v in G2.BONF_CELLS})
    # 3. 從 b5bc39f2cd 的 main_excess 獨立重算 99.72% CI
    MX = pd.read_csv(io.BytesIO(_show(f"{od}/main_excess.csv.gz")), compression="gzip", dtype={"sid": str, "月": "int64"}, encoding="utf-8-sig",
                     keep_default_na=False, na_values=[""], float_precision="round_trip")
    bad = []
    for r in q.itertuples(index=False):
        c, v, nm = r.cell[:2], r.cell[2:], r.stat.split("｜")[0]
        m = MX[(MX["格"] == c) & (MX["版"] == v) & (MX["段"] == nm)]
        cb = G.cluster_boot(m["超額"].to_numpy(float), m["月"].to_numpy(), alpha=0.05 / 18)
        c99 = G.cluster_boot(m["超額"].to_numpy(float), m["月"].to_numpy())
        if not (cb["lo"] == float(r.lo_bonf18) and cb["hi"] == float(r.hi_bonf18) and c99["lo"] == float(r.lo) and c99["hi"] == float(r.hi)):
            bad.append(r.cell + r.stat)
    ok("由 b5bc39f2cd main_excess 獨立重算：99% CI ＝ 原值、99.72% CI ＝ 新欄（48 列）", not bad, str(bad[:3]))
    T = J["Bonferroni18格CI"]
    ok("formal.json Bonferroni 表：alpha 0.05/18、nboot／seed 同 99% CI、18 格清單、與 desc.csv 同值",
       abs(T["alpha"] - 0.05 / 18) < 1e-15 and T["nboot"] == G.NBOOT and T["seed"] == G.SEED and len(T["18格(確認段)"]) == 18
       and all(T["表"][f"{r.cell[:2]}|{r.cell[2:]}"][r.stat.split("｜")[0]]["Bonferroni18格99.72%CI"] == [float(r.lo_bonf18), float(r.hi_bonf18)]
               and T["表"][f"{r.cell[:2]}|{r.cell[2:]}"][r.stat.split("｜")[0]]["99%CI"] == [float(r.lo), float(r.hi)] for r in q.itertuples(index=False)))
    # 4. result_sentences.txt
    P = open(os.path.join(root, od, "result_sentences.txt"), encoding="utf-8").read().strip().split("\n\n")
    ok("result_sentences 每段都附新固定句、無舊句", len(P) == 5 + 24 and all(p.endswith(NEW_PHRASE) for p in P) and OLD_PHRASE not in "".join(P))
    ok("result_sentences ★S4、★S6、★S8、★S9 註恰一行、不判定不加 N 一行",
       sum("★S4、★S6、★S8、★S9" in p for p in P) == 1 and sum(G2.NO_VERDICT_LINE in p for p in P) == 1)
    ok("result_sentences 每句兩段的 99% CI 旁都有 99.72% CI（不只列 99%）",
       all(p.count("月分群 99% CI") == 2 and p.count(G2.BONF_LAB) == 2 for p in P[5:]))
    raised = []
    for p in P:
        try:
            G2.guard(p)
        except ValueError as e:
            raised.append(str(e))
    ok("result_sentences 全部過擋門（無判定措辭）", not raised, str(raised[:2]))
    ok("result_sentences 句子與 formal.json 結果句一致", P[5:] == list(J["結果句"].values()))
    # 5. 其他正式輸出未動
    others = [f for f in os.listdir(os.path.join(root, od)) if f not in ("formal.json", "desc.csv", "result_sentences.txt")]
    d = subprocess.run(["git", "diff", "--quiet", G2.BASE_COMMIT, "--"] + [f"{od}/{f}" for f in others], cwd=root).returncode
    ok(f"正式輸出其餘 {len(others)} 檔（events、main_excess、run.log…）與 b5bc39f2cd 相同", d == 0 and len(others) >= 30)


def main():
    for f in (t_a0_equiv, t_buy1, t_buy2, t_buy3, t_exit, t_ret_one, t_sentence_gate, t_outputs, t_formal):
        f()
    n = len(RES); p = sum(1 for _, x in RES if x)
    print(f"\n自測 {p}/{n} 通過")
    sys.exit(0 if p == n else 1)


if __name__ == "__main__":
    main()

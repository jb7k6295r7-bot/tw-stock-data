# -*- coding: utf-8 -*-
"""USREG-C3s（動能只在 S&P 500）——裁定 seq336 §三發號（sha 8fb8bd723ec4964d；美股 N ＋1，判定只用早年段 ① 或前瞻 ②）。
登錄：美股策略線 seq1，2026-10-11 10:16（台北）「登錄全文-USREG-C3s_動能只在SP500_seq1_美股策略線_sha8fb8bd723ec4964d-3932B-20261011-1016.md」（整檔 sha 已核）。
本次只做描述 a～c（2016-12～2026-09 是看過段 ⇒ ⛔ 只描述、不判）；早年段 ① 等資料庫；前瞻 ② 只出樣板。

    cd ~/tw-p17 && PYTHONPATH=$HOME/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchUSC3s [--procs 3]
    獨立查核：... -m backtest.researchUSC3s --check

重用：researchUSC（K：rworld、rank_tables、book、rank_main、run_random、metrics、label）、researchUSC_c3.mom_scores、researchUSA4.sim_book（閘）、
資料 ＝ C 批同一份（~/us_work/a4/world.npz，us-stock-data 881c86a，經 researchUSA2_data 聯集轉接層產出）。⛔ 不改既有程式與結果夾（resultsUSC/*.json）。

═══ C3s 補讀法（S 標；⭐ 寫死於 2026-10-11 10:30（台北）；寫死前已知只有登錄所引 C3「只 S&P 500」欄的年化／回落／比值與 C3 合併欄假訊號，
    ⛔ 沒看本件 b、c、變體 V、逐年任何數字）═══
 S1 規則 ＝ C3 逐字（C3-1、C3-2、K3）只換母體：MOM ＝ researchUSC_c3.mom_scores()（12−1，錨點 5 根有效、⛔ 跨斷點）；排名母體 ＝ e−1 當天在 S&P 500
    （world m5，point-in-time）且 MOM 可算者，同分依代號序；前 10%（無條件進位，分母 ＝ S&P 500 內可排檔數）＝ 進場名單（依 MOM 遞減補空槽）；
    前 20% ＝ 續抱名單；持股掉出前 20% 或掉出指數 ⇒ e 開盤賣；8 槽等權；成本 0.05%（賣出時扣進場金額 × 0.05%）；無固定天數、無停損停利。
 S2 同算法核對（登錄 §一 ⚠）：C3「只500」欄 ＝ K.rank_tables(S12, memb["只500"]) ⇒ 先限 S&P 500 再排 ＝ 本規則。核對 ＝
    本檔主臂年化 與 resultsUSC/C3.json 三欄.只500.年化 差 ≤ 1e−12，且回落、出場筆數相同 ⇒ 判「同算法」。
    另報變體 V「合併排名後篩 500」（描述）：進場 ＝ 合併（500∪400）前 10% 中屬 S&P 500 者（依 MOM 序）、續抱 ＝ 合併前 20% 中屬 S&P 500 者。
 S3 a 看過段 ＝ [2016-12-30 收盤, 2026-09-30]（同 C3；第一個換股日 2017-01-03）：年化、回落、比值、K2 對照語（⛔ 只描述、不當判定）、每年換手、
    持有天數分佈、窗尾仍持有、離頂多近；成本敏感度 0.02%、0.10%；逐年報酬（2017～2025 曆年；2026 ＝ 1～9 月）與 ^SP500TR 同段。
 S4 b 集中度：記帳版換股簿 ledger_book（K.book 同式，另記每筆進場金額與股數；閘：權益與 K.book 逐日差 ≤ 1e−12）。
    每檔損益（1.0 起算的金額）＝ Σ 已出場筆（出場價 × 股數 − 進場金額 − 進場金額 × 成本）＋ 窗尾未出場（2026-09-30 收盤 × 股數 − 進場金額，不扣賣出成本）；
    同一檔多次進出合併；恆等式 Σ 每檔損益 ＝ 權益(2026-09-30) − 1（≤ 1e−9）。
    總獲利 ＝ Σ 每檔損益（淨）；前 3／前 10 檔 ＝ 每檔損益最大者；占比 ＝ 其和 ÷ 總獲利（另報 ÷ 賺錢檔損益和）。
    拿掉前 3 檔：主 ＝ 三檔整段自排名母體移除（rank_tables excl：不排、不占分母）後重跑換股簿（槽位由下一名補）；
    副 ＝ 不重跑、權益直接扣三檔損益：(1 ＋ 總獲利 − 三檔損益) 以同窗年數年化（回落不報）。
 S5 c 假訊號（同 C3-6，母體換 S&P 500）：每個換股日從「e−1 在 S&P 500 且 e 有效」者隨機挑股補空槽；每筆抱的換股期數從本主臂已出場「換股」筆的
    持有換股期數分佈抽（同換手）；200 次；rng ＝ default_rng([20261011, 336, 3, r])；p ＝ 隨機年化 ＞ ^SP500TR 的比例；另報隨機年化 ≥ 主臂的比例。
 S6 早年段 ①（2000-01～2015-12）與描述 d、e：⛔ 本次不做——資料庫尚未把 S&P 500 成分往前延伸到 1999、未含已下市股還原價 ⇒ 等資料庫（覆蓋率 ≥ 95% 才可判）。
 S7 前瞻 ②：forward_template.csv ＝ 第 0 列（起點：2026-10 最後一個交易日收盤選出、11 月第一個交易日開盤買的 8 檔）＋ 36 列（2026-11～2029-10 每月）；
    月報酬 ＝ 上月最後一個交易日收盤 → 本月最後一個交易日收盤（策略照 S1 換股簿、^SP500TR 同段）；滿 36 列（2029-10 月底）第一次判、中途只報不判。
 S8 --check（獨立寫法，⛔ 不呼叫 K.book／K.rank_tables／mom_scores／ledger_book／sim_book）：
    X1 抽 15 個換股日，逐股迴圈另算 MOM、在 S&P 500 內排 ⇒ 前 10%、前 20% 集合 對 本檔名單；
    X2 另寫逐日換股簿（dict 記帳）重算主臂權益，抽 40 個交易日比對（≤ 1e−9）＋ 窗尾值；
    X3 另算每檔損益，比對前 10 檔代號與損益（≤ 1e−9）＋ 恆等式。不同數合計要 0。
 S9 私有資料：resultsUSC/C3s/ 只放彙總與代號（持股代號、前 10 檔代號與占比）；逐日權益、逐筆成交寫 ~/us_work/c/c3s/（repo 外）並列 sha。
 S10 存活者偏差（必寫，同 K10）：S&P 500 有 18 檔不在母體 ⇒ 偏向存活股、偏樂觀。
"""
from __future__ import annotations

import argparse
import csv
import html
import json
import os
import sys
import time
from collections import Counter, defaultdict

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17"))
from backtest import researchUSC as K          # noqa: E402
from backtest import researchUSC_c3 as C3      # noqa: E402

READ_TS = "2026-10-11 10:30（台北）"
SHA = "8fb8bd723ec4964d"
RULING = "裁定 seq336 §三（2026-10-11 10:19）"
REGFILE = "登錄全文-USREG-C3s_動能只在SP500_seq1_美股策略線_sha8fb8bd723ec4964d-3932B-20261011-1016.md"
OUTD = os.path.join(K.OUT, "C3s")
WORKD = os.path.join(K.WORK, "c3s")
HTMLN = "美股動能只在SP500_描述.html"
FAKE_SEED = (20261011, 336, 3)


def jd(obj, name):
    os.makedirs(OUTD, exist_ok=True)
    return K.jdump(obj, os.path.join(OUTD, name))


# ═════════════ 記帳版換股簿（S4；K.book 同式＋每筆金額）═════════════
def ledger_book(Wd, keep, buy, N, t0, t1, cost=K.COST):
    O, CF, valid, last, brk = Wd["O"], Wd["CF"], Wd["valid"], Wd["last"], Wd["pb"]
    n = len(Wd["cal"]); eq = np.ones(n); cash = 1.0; pos = {}; pend = set()
    rset = set(int(e) for e in keep if t0 <= e <= t1)
    pnl = defaultdict(float); fills = []
    for t in range(t0, t1 + 1):
        for j in list(pos):
            u, amt, b, hi = pos[j]
            if t > b and brk[t, j]:
                px = CF[t - 1, j]
            elif t > last[j]:
                px = CF[last[j], j]
            else:
                continue
            pos.pop(j); pend.discard(j)
            cash += u * px - amt * cost; pnl[j] += u * px - amt - amt * cost; fills.append((j, b, t, amt, u * px))
        isreb = t in rset
        if isreb:
            ks = keep.get(t, set())
            pend |= (set(pos) - set(ks)); pend -= set(ks)
        for j in sorted(pend):
            if j not in pos:
                pend.discard(j); continue
            o_t = O[t, j]
            if not (valid[t, j] and np.isfinite(o_t) and o_t > 0):
                continue
            u, amt, b, hi = pos.pop(j)
            cash += u * o_t - amt * cost; pnl[j] += u * o_t - amt - amt * cost; fills.append((j, b, t, amt, u * o_t)); pend.discard(j)
        if isreb:
            free = N - len(pos)
            for j in [j for j in buy.get(t, []) if j not in pos][:max(free, 0)]:
                o_t = O[t, j]
                if not (valid[t, j] and np.isfinite(o_t) and o_t > 0):
                    continue
                amt = min(eq[t - 1] / N, cash)
                if amt <= 1e-12:
                    break
                cash -= amt; pos[j] = [amt / o_t, amt, t, o_t]
        hv = 0.0
        for j, p in pos.items():
            c = CF[t, j]; hv += p[0] * c
            if c > p[3]:
                p[3] = c
        eq[t] = cash + hv
    eq[t1 + 1:] = eq[t1]
    for j, p in pos.items():
        pnl[j] += p[0] * CF[t1, j] - p[1]
    return eq, dict(pnl), sorted(pos), fills


def yearly(eq, B, cal, a0, w1):
    out = {}
    yrs = sorted(set(int(y) for y in cal[a0 + 1:w1 + 1].year))
    for y in yrs:
        idx = np.flatnonzero(np.asarray(cal.year) == y)
        b = min(int(idx[-1]), w1); a = max(int(idx[0]) - 1, a0)
        out[str(y) + ("（1～9 月）" if b == w1 and cal[b].month < 12 else "")] = {
            "策略": float(eq[b] / eq[a] - 1), "^SP500TR": float(B[b] / B[a] - 1)}
    return out


def sl(s, keys=("年化", "回落", "比值", "標籤", "每年換手")):
    return {k: s.get(k) for k in keys}


def run(a):
    T0 = time.time()
    os.makedirs(OUTD, exist_ok=True); os.makedirs(WORKD, exist_ok=True)
    R = K.rworld(); W = R["Wd"]; cal = R["cal"]; w1 = R["w1"]; A4 = R["A4"]; tick = W["tick"]
    M5 = R["memb"]["只500"]; MC = R["memb"]["合併"]
    S12 = C3.mom_scores()
    t0 = min(e for e, v in S12.items() if np.isfinite(v).any()); a0 = t0 - 1
    BUY, KEEP, ORD = K.rank_tables(S12, M5)
    res, tr, s, bm = K.rank_main(KEEP, BUY, t0, w1, a0, w1)
    gates = {}
    # 閘 1：ledger_book ＝ K.book
    leq, pnl, openj, fills = ledger_book(W, KEEP, BUY, K.N_SLOTS, t0, w1)
    gates["ledger_book 對 K.book 最大差"] = float(np.max(np.abs(leq - res["eq"])))
    tot = float(res["eq"][w1] - 1); gates["恆等式 |Σ損益 −（權益−1）|"] = abs(sum(pnl.values()) - tot)
    if gates["ledger_book 對 K.book 最大差"] > 1e-12 or gates["恆等式 |Σ損益 −（權益−1）|"] > 1e-9:
        jd({"⛔": "閘不過", **gates}, "gate_fail.json"); raise SystemExit("C3s 閘不過")
    # 閘 2（描述）：sim_book（sel ＝ 續抱名單依序）
    sb = A4.sim_book(ORD, W, K.N_SLOTS, t0, w1)
    gates["sim_book（sel＝前20%依序）最大差"] = float(np.max(np.abs(sb["eq"] - res["eq"])))
    # S2 同算法
    c3j = json.load(open(os.path.join(K.OUT, "C3.json"), encoding="utf-8"))["三欄"]["只500"]
    same = (abs(c3j["年化"] - s["年化"]) <= 1e-12 and abs(c3j["回落"] - s["回落"]) <= 1e-12 and c3j["出場筆數"] == s["出場筆數"])
    BUYc, KEEPc, _ = K.rank_tables(S12, MC)
    BUYv = {e: [j for j in v if M5[e - 1, j]] for e, v in BUYc.items()}
    KEEPv = {e: {j for j in v if M5[e - 1, j]} for e, v in KEEPc.items()}
    _, trv, sv, _ = K.rank_main(KEEPv, BUYv, t0, w1, a0, w1)
    diffm = sum(1 for e in BUY if set(BUY[e]) != set(BUYv[e]))
    S2 = {"C3「只500」欄寫法": "K.rank_tables(S12, memb['只500']) ⇒ 先限 S&P 500 再排（分母 ＝ 500 內可排檔數）",
          "與本規則同算法": bool(same), "C3.json 只500 年化": c3j["年化"], "本檔主臂年化": s["年化"], "差": abs(c3j["年化"] - s["年化"]),
          "變體 V 合併排名後篩 500（描述）": {**sl(sv), "持有天數_中位": sv.get("持有天數_中位"), "窗尾仍持有（檔）": sv.get("窗尾仍持有（檔）")},
          "進場名單與變體 V 不同的換股日": f"{diffm}／{len(BUY)}"}
    K.log("[C3s] 閘 %s｜同算法 %s" % (gates, same), "c3s.log")
    # a
    A = {**{k: s.get(k) for k in ("年化", "回落", "比值", "每年換手", "成本／年", "平均持股", "現金比例", "出場筆數", "窗尾仍持有（檔）",
                                   "持有天數_平均", "持有天數_中位", "持有天數_p10", "持有天數_p90", "持有天數_最長", "離頂多近_中位", "出場勝率", "出場原因")},
         "K2 對照語（⛔ 看過段只描述、不判）": s["標籤"], "^SP500TR": bm,
         "年化差（點）": (s["年化"] - bm["年化"]) * 100}
    A["成本敏感度"] = {}
    for c_ in K.COST_SENS:
        _, _, sc_, _ = K.rank_main(KEEP, BUY, t0, w1, a0, w1, cost=c_, trades=False)
        A["成本敏感度"][f"{c_:.2%}"] = sl(sc_, ("年化", "回落", "比值"))
    A["逐年"] = yearly(res["eq"], R["B"], cal, a0, w1)
    A["窗尾持股（2026-09-30）"] = [str(tick[j]) for j in sorted(openj, key=lambda j: str(tick[j]))]
    # b
    ser = pd.Series({int(j): v for j, v in pnl.items()}).sort_values(ascending=False)
    gains = float(ser[ser > 0].sum())
    top = [{"代號": str(tick[j]), "損益（1.0 起算）": float(v), "占總獲利": float(v / tot), "窗尾仍持有": bool(j in openj)} for j, v in ser.head(10).items()]
    top3 = [int(j) for j in ser.index[:3]]
    excl = {}
    for e in S12:
        m = np.zeros(len(tick), bool); m[top3] = True; excl[e] = m
    Bx, Kx, _ = K.rank_tables(S12, M5, excl=excl)
    _, _, sx, _ = K.rank_main(Kx, Bx, t0, w1, a0, w1)
    yrs = (w1 - a0) / 252
    sub = float(ser.iloc[:3].sum())
    Bb = {"總獲利（權益−1）": tot, "交易過檔數": int(len(ser)), "賺錢檔數": int((ser > 0).sum()),
          "前3檔占總獲利": float(ser.iloc[:3].sum() / tot), "前10檔占總獲利": float(ser.iloc[:10].sum() / tot),
          "前3檔占賺錢檔損益和": float(ser.iloc[:3].sum() / gains), "前10檔占賺錢檔損益和": float(ser.iloc[:10].sum() / gains),
          "前10檔": top,
          "拿掉前3檔（主：自母體移除重跑）": {**sl(sx), "對 ^SP500TR 年化差（點）": (sx["年化"] - bm["年化"]) * 100},
          "拿掉前3檔（副：權益直接扣損益）": {"年化": float((1 + tot - sub) ** (1 / yrs) - 1)}}
    K.log("[C3s] a、b 完成 %.0fs" % (time.time() - T0), "c3s.log")
    # c 假訊號
    ms = np.array(sorted(BUY))
    hl = np.array([max(1, int(np.searchsorted(ms, x[2], side="right") - 1 - np.searchsorted(ms, x[1], side="left")))
                   for x in tr if x[5] == "換股"], int)

    def gen_fake(r):
        rng = np.random.default_rng([*FAKE_SEED, r]); rem = {}

        def kf(t, held):
            keep = set()
            for j in held:
                rem[j] = rem.get(j, 1) - 1
                if rem[j] > 0:
                    keep.add(j)
            return keep

        def bf(t, held):
            el = np.flatnonzero(M5[t - 1] & W["valid"][t])
            return [int(x) for x in rng.permutation(el)[:40]]

        def ob(j, t):
            rem[j] = int(rng.choice(hl))
        return kf, bf, ob
    c, m, tv = K.run_random(gen_fake, t0, w1, a0, w1, a.seeds, a.procs)
    FK = K.rand_summary(c, m, tv, bm, s["年化"])
    FK.update({"主臂持有換股期數中位": float(np.median(hl)), "主臂每年換手": s["每年換手"], "隨機年化 p10": float(np.percentile(c, 10)),
               "隨機年化 p90": float(np.percentile(c, 90)), "rng": f"default_rng([{FAKE_SEED[0]}, {FAKE_SEED[1]}, {FAKE_SEED[2]}, r])，r＝0～{a.seeds - 1}"})
    K.log("[C3s] 假訊號 %.0fs" % (time.time() - T0), "c3s.log")
    # 先驗（只列看過段 b、c；① 與覆蓋率等資料庫）
    pri = [{"先驗": "b 看過段前 3 檔占總獲利 ≥ 40%（約六成）", "結果": f"{Bb['前3檔占總獲利']:.1%}", "對": bool(Bb["前3檔占總獲利"] >= 0.40)},
           {"先驗": "b 拿掉前 3 檔後年化 ＜ ^SP500TR（約五成五）", "結果": f"{sx['年化']:+.1%} vs {bm['年化']:+.1%}", "對": bool(sx["年化"] < bm["年化"])},
           {"先驗": "c 假訊號 p ≥ 5%（約四成）", "結果": f"{FK['p（隨機年化 ＞ ^SP500TR）']:.1%}", "對": bool(FK["p（隨機年化 ＞ ^SP500TR）"] >= 0.05)},
           {"先驗": "① 早年段合格約三成／另列約三成／不合格約四成", "結果": "等資料庫", "對": None},
           {"先驗": "資料覆蓋率能達 95%（約四成）", "結果": "等資料庫", "對": None}]
    # 存 repo 外
    pk = os.path.join(WORKD, "c3s_eq_trades.pkl")
    pd.to_pickle({"eq": res["eq"], "tr": tr, "pnl": pnl, "fills": fills, "eq_V": None}, pk)
    out = {"件": "USREG-C3s 動能只在 S&P 500", "登錄": f"美股策略線 seq1 sha {SHA}（{REGFILE}）", "裁定": RULING, "N": "美股帳 ＋1（判定 ① 時用；② 判時再 ＋1）",
           "本次範圍": "描述 a～c（看過段 2016-12-30～2026-09-30，⛔ 只描述、不判）；① 早年段等資料庫；② 前瞻出樣板",
           "總標籤": "未判（① 等資料庫、② 前瞻 2026-10 月底起記，2029-10 月底第一次判）",
           "a 看過段": A, "b 集中度": Bb, "c 假訊號": FK, "S2 與 C3 只500欄": S2, "閘": gates, "先驗": pri,
           "早年段 ①": "⛔ 本次不做：資料庫尚未把 S&P 500 成分延伸到 1999、未含已下市股還原價 ⇒ 等資料庫（覆蓋率 ≥ 95% 才可判；d、e 同）",
           "存活者偏差": "S&P 500 有 18 檔不在母體 ⇒ 偏向存活股、偏樂觀（同 C 批 K10）",
           "第一個換股日": str(cal[t0].date()), "窗": [str(cal[a0].date()), str(cal[w1].date())],
           "補讀法": f"S1～S10（researchUSC3s.py docstring，{READ_TS} 寫死）；沿用 C3-1、C3-2、K2、K3",
           "資料": {"world": "~/us_work/a4/world.npz（us-stock-data 881c86a）", "repo 外": {"檔": pk, "sha256": K.sha256f(pk)}},
           "算於": K.now_tpe() + "（台北）", "秒": round(time.time() - T0)}
    jd(out, "summary.json")
    forward_template(out)
    write_report(out)
    write_html(out)
    K.log("[C3s] 完成 %.0fs" % (time.time() - T0), "c3s.log")
    return out


# ═════════════ 前瞻樣板（S7）═════════════
def forward_template(out):
    cols = ["期", "月份", "量測月底（上月最後交易日）", "換股日（本月第一個交易日）", "月底（本月最後交易日）",
            "持股1", "持股2", "持股3", "持股4", "持股5", "持股6", "持股7", "持股8", "本月新進", "本月賣出", "賣出原因（跌出前20%／掉出指數／下市）",
            "S&P500 可排檔數", "前10%門檻檔數", "策略月報酬", "^SP500TR 月報酬", "策略累積", "^SP500TR 累積", "成分快照來源與日期", "價格資料 commit", "記錄時間（台北）", "備註"]
    rows = [["0", "起點 2026-10", "", "", "2026-10 最後交易日", *[""] * 8, "", "", "", "", "", "—", "—", "1.0000", "1.0000", "", "", "",
             "起點：2026-10 最後交易日收盤算 MOM、在 S&P 500 內排，11 月第一個交易日開盤買前 10% 中 MOM 最高 8 檔"]]
    y, mth = 2026, 11
    for i in range(1, 37):
        note = "⭐ 滿 36 個月：第一次判（② 對 ^SP500TR 同窗）" if i == 36 else ("中途只報不判" if i in (12, 24) else "")
        rows.append([str(i), f"{y}-{mth:02d}", "", "", "", *[""] * 8, "", "", "", "", "", "", "", "", "", "", "", "", note])
        mth += 1
        if mth > 12:
            y, mth = y + 1, 1
    p = os.path.join(OUTD, "forward_template.csv")
    with open(p, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f); w.writerow(cols); w.writerows(rows)
    return p


def pc(x, d=1, sign=True):
    return "—" if x is None else (f"{x * 100:+.{d}f}%" if sign else f"{x * 100:.{d}f}%")


def write_report(o):
    A, B, F, S2 = o["a 看過段"], o["b 集中度"], o["c 假訊號"], o["S2 與 C3 只500欄"]
    bm = A["^SP500TR"]; x = B["拿掉前3檔（主：自母體移除重跑）"]
    L = ["# USREG-C3s 動能只在 S&P 500｜描述 a～c（看過段，⛔ 不判）", "",
         f"算於 {o['算於']}｜{o['裁定']}｜登錄 sha {SHA}｜補讀法 S1～S10（{READ_TS} 寫死）", "",
         "## 結論先講", "",
         f"- 看過段 2016-12-30～2026-09-30：年化 {pc(A['年化'])}（^SP500TR {pc(bm['年化'])}），回落 {pc(A['回落'])}（^SP500TR {pc(bm['回落'])}），"
         f"比值 {A['比值']:.2f}（^SP500TR {bm['比值']:.2f}）；每年換手 {A['每年換手']:.2f} 倍。⛔ 母體是看過結果才縮的 ⇒ 只描述、不判。",
         f"- 集中度：前 3 檔占總獲利 {pc(B['前3檔占總獲利'], sign=False)}、前 10 檔 {pc(B['前10檔占總獲利'], sign=False)}；"
         f"拿掉前 3 檔（{'、'.join(t['代號'] for t in B['前10檔'][:3])}）重跑：年化 {pc(x['年化'])}、回落 {pc(x['回落'])}"
         f"（扣損益不重跑：{pc(B['拿掉前3檔（副：權益直接扣損益）']['年化'])}）。",
         f"- 假訊號（S&P 500 內隨機 8 檔、同換手，200 次）：年化中位 {pc(F['年化中位'])}，贏 ^SP500TR 的比例 p ＝ {pc(F['p（隨機年化 ＞ ^SP500TR）'], sign=False)}；"
         f"隨機年化 ≥ 主臂 {pc(F['隨機年化 ≥ 主臂 的比例'], sign=False)}。",
         f"- 與 C3「只 S&P 500」欄：{'同一算法（排名都在 500 內），數字逐位相同' if S2['與本規則同算法'] else '⚠ 不同算法'}；"
         f"變體「合併排名後篩 500」另報：年化 {pc(S2['變體 V 合併排名後篩 500（描述）']['年化'])}、回落 {pc(S2['變體 V 合併排名後篩 500（描述）']['回落'])}。",
         "- 早年段 2000～2015（判定 ①）：⛔ 這次不做，**等資料庫**（成分往前延伸到 1999、含已下市股還原價；覆蓋率 ≥ 95% 才可判）。",
         "- 前瞻（判定 ②）：樣板 forward_template.csv，2026-10 月底起記，2029-10 月底第一次判。", "",
         "## a 看過段", "", "| 項 | 策略 | ^SP500TR |", "|---|---|---|",
         f"| 年化 | {pc(A['年化'])} | {pc(bm['年化'])} |", f"| 最大回落 | {pc(A['回落'])} | {pc(bm['回落'])} |", f"| 比值 | {A['比值']:.2f} | {bm['比值']:.2f} |",
         f"| 每年換手 | {A['每年換手']:.2f} 倍 | — |", "",
         f"K2 對照語（只描述）：{A['K2 對照語（⛔ 看過段只描述、不判）']}。成本 0.02%：{pc(A['成本敏感度']['0.02%']['年化'])}；0.10%：{pc(A['成本敏感度']['0.10%']['年化'])}。",
         f"條件出場（seq308）：出場 {A['出場筆數']} 筆、持有天數中位 {A['持有天數_中位']:.0f}（p10 {A['持有天數_p10']:.0f}、p90 {A['持有天數_p90']:.0f}、最長 {A['持有天數_最長']:.0f}）、"
         f"窗尾仍持有 {A['窗尾仍持有（檔）']} 檔、離頂多近中位 {pc(A['離頂多近_中位'])}。", "",
         "逐年：", "", "| 年 | 策略 | ^SP500TR |", "|---|---|---|"]
    for y, v in A["逐年"].items():
        L.append(f"| {y} | {pc(v['策略'])} | {pc(v['^SP500TR'])} |")
    L += ["", "## b 集中度", "", f"總獲利（1.0 起算）{B['總獲利（權益−1）']:.2f}；交易過 {B['交易過檔數']} 檔、賺錢 {B['賺錢檔數']} 檔。"
          f"前 3 檔占賺錢檔損益和 {pc(B['前3檔占賺錢檔損益和'], sign=False)}、前 10 檔 {pc(B['前10檔占賺錢檔損益和'], sign=False)}。", "",
          "| 名次 | 代號 | 占總獲利 | 窗尾仍持有 |", "|---|---|---|---|"]
    for i, t in enumerate(B["前10檔"], 1):
        L.append(f"| {i} | {t['代號']} | {pc(t['占總獲利'], sign=False)} | {'是' if t['窗尾仍持有'] else '否'} |")
    L += ["", f"拿掉前 3 檔（自母體移除重跑）：年化 {pc(x['年化'])}、回落 {pc(x['回落'])}、比值 {x['比值']:.2f}；對 ^SP500TR 年化差 {x['對 ^SP500TR 年化差（點）']:+.1f} 點。", "",
          "## c 假訊號", "", f"S&P 500 內每月隨機補 8 檔、抱的期數照主臂分佈抽（主臂持有換股期數中位 {F['主臂持有換股期數中位']:.0f}）；200 次。",
          f"隨機年化中位 {pc(F['年化中位'])}（p10 {pc(F['隨機年化 p10'])}、p90 {pc(F['隨機年化 p90'])}）、回落中位 {pc(F['回落中位'])}、每年換手中位 {F['每年換手中位']:.2f}（主臂 {F['主臂每年換手']:.2f}）。",
          f"p（隨機年化 ＞ ^SP500TR）＝ {pc(F['p（隨機年化 ＞ ^SP500TR）'], sign=False)}；隨機 ≥ 主臂 {pc(F['隨機年化 ≥ 主臂 的比例'], sign=False)}。rng {F['rng']}。", "",
          "## 與 C3「只 S&P 500」欄", "", f"- C3 寫法：{S2['C3「只500」欄寫法']}。本規則（排名只在 S&P 500 內）＝ 同算法：{'是' if S2['與本規則同算法'] else '否'}（年化差 {S2['差']:.1e}）。",
          f"- 變體 V（合併 500∪400 排名後篩 500，描述）：年化 {pc(S2['變體 V 合併排名後篩 500（描述）']['年化'])}、回落 {pc(S2['變體 V 合併排名後篩 500（描述）']['回落'])}、"
          f"比值 {S2['變體 V 合併排名後篩 500（描述）']['比值']:.2f}；進場名單不同的換股日 {S2['進場名單與變體 V 不同的換股日']}。⭐ 判定照本規則。", "",
          "## 先驗對錯", ""]
    for p in o["先驗"]:
        L.append(f"- {p['先驗']}：{p['結果']}（{'對' if p['對'] else ('錯' if p['對'] is False else '—')}）")
    L += ["", "## 前瞻紀錄讀法（S7）", "",
          "- 每月最後一個交易日收盤後：用 S&P 500 當天成分（point-in-time），算 MOM ＝ 上上月底收盤 ÷ 13 個月前月底收盤 − 1，在 500 內排；前 10% 進、前 20% 續抱。",
          "- 次月第一個交易日開盤：先賣跌出前 20% 或掉出指數者、再依 MOM 由高到低補空槽（8 槽等權、每槽 ＝ 前一日權益 ÷ 8）。",
          "- 月報酬 ＝ 上月最後交易日收盤 → 本月最後交易日收盤；^SP500TR 同段。成本 0.05%（賣出時扣進場金額）。",
          f"- 參考：看過段窗尾（2026-09-30）持股 {', '.join(A['窗尾持股（2026-09-30）'])}；面板止於 2026-09-30，2026-10 月初換股未模擬。",
          "- 滿 36 期（2029-10 月底）第一次判；中途只報不判。", "",
          "## 閘與查核", "", f"- {json.dumps(o['閘'], ensure_ascii=False)}", "- --check 結果見 check.json。", "",
          "## 限制", "", f"- {o['存活者偏差']}。", "- 看過段只有約 10 年；登錄已寫明大型股領漲年代的解釋同時是風險。",
          "- resultsUSC/C3s/ 只放彙總與代號；逐日權益、逐筆成交在 repo 外（~/us_work/c/c3s/）。"]
    open(os.path.join(OUTD, "REPORT.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")


def write_html(o):
    A, B, F, S2 = o["a 看過段"], o["b 集中度"], o["c 假訊號"], o["S2 與 C3 只500欄"]
    bm = A["^SP500TR"]; x = B["拿掉前3檔（主：自母體移除重跑）"]; V = S2["變體 V 合併排名後篩 500（描述）"]
    e = html.escape
    ck = None
    cp = os.path.join(OUTD, "check.json")
    if os.path.exists(cp):
        ck = json.load(open(cp, encoding="utf-8"))
    H = ["<!doctype html><html lang='zh-Hant'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>",
         "<title>美股動能只在SP500</title><style>",
         ":root{--bg:#fff;--fg:#1f2328;--mut:#5c6670;--bd:#d8dee4;--th:#f3f4f6;--kb:#fff7e6;--kl:#d97706;--up:#15803d;--dn:#b91c1c}",
         "@media (prefers-color-scheme:dark){:root:not([data-theme='light']){--bg:#15181c;--fg:#e6e8eb;--mut:#9aa4ae;--bd:#2f363d;--th:#1f242a;--kb:#2a2216;--kl:#f59e0b;--up:#4ade80;--dn:#f87171}}",
         ":root[data-theme='dark']{--bg:#15181c;--fg:#e6e8eb;--mut:#9aa4ae;--bd:#2f363d;--th:#1f242a;--kb:#2a2216;--kl:#f59e0b;--up:#4ade80;--dn:#f87171}",
         "body{background:var(--bg);color:var(--fg);font-family:system-ui,'Noto Sans TC',sans-serif;margin:0 auto;max-width:880px;padding:16px;line-height:1.65}",
         "table{border-collapse:collapse;width:100%;font-size:14px}td,th{border:1px solid var(--bd);padding:6px 8px;text-align:left}th{background:var(--th)}",
         "td.n{text-align:right;font-variant-numeric:tabular-nums}.w{overflow-x:auto}.k{background:var(--kb);border-left:4px solid var(--kl);padding:10px 14px;margin:14px 0}",
         "h2{border-bottom:2px solid var(--bd);padding-bottom:4px;margin-top:28px;font-size:1.15em}small,.m{color:var(--mut)}.up{color:var(--up)}.dn{color:var(--dn)}</style></head><body>",
         "<h1>美股動能只在 S&amp;P 500｜看過段描述</h1>",
         f"<p class='m'><small>USREG-C3s｜{e(o['裁定'])}｜登錄 sha {SHA}｜算於 {e(o['算於'])}｜⛔ 看過段只描述、不判｜只放彙總</small></p>",
         "<div class='k'><b>結論先講：</b>"
         f"2016-12～2026-09 這段（看過）年化 <b>{pc(A['年化'])}</b>，^SP500TR {pc(bm['年化'])}；回落 {pc(A['回落'])}（大盤 {pc(bm['回落'])}）。"
         f"獲利集中：前 3 檔占 <b>{pc(B['前3檔占總獲利'], sign=False)}</b>，拿掉這 3 檔重跑年化 {pc(x['年化'])}。"
         f"S&amp;P 500 裡隨機挑 8 檔、同樣換手，200 次中 {pc(F['p（隨機年化 ＞ ^SP500TR）'], sign=False)} 贏大盤。"
         "<br>⛔ 這段是看過結果才縮母體的，不能拿來判；判定要等 <b>早年段 2000～2015（等資料庫）</b> 或 <b>前瞻 36 個月（2029-10 月底）</b>。</div>",
         "<h2>a 看過段 2016-12-30～2026-09-30</h2><div class='w'><table><tr><th>項</th><th>策略</th><th>^SP500TR</th></tr>",
         f"<tr><td>年化</td><td class='n'>{pc(A['年化'])}</td><td class='n'>{pc(bm['年化'])}</td></tr>",
         f"<tr><td>最大回落</td><td class='n'>{pc(A['回落'])}</td><td class='n'>{pc(bm['回落'])}</td></tr>",
         f"<tr><td>比值（年化÷回落）</td><td class='n'>{A['比值']:.2f}</td><td class='n'>{bm['比值']:.2f}</td></tr>",
         f"<tr><td>每年換手</td><td class='n'>{A['每年換手']:.2f} 倍</td><td class='n'>—</td></tr></table></div>",
         f"<p class='m'><small>持有天數中位 {A['持有天數_中位']:.0f}、窗尾仍持有 {A['窗尾仍持有（檔）']} 檔；成本 0.10% 時年化 {pc(A['成本敏感度']['0.10%']['年化'])}。</small></p>",
         "<div class='w'><table><tr><th>年</th><th>策略</th><th>^SP500TR</th><th>差（點）</th></tr>"]
    for y, v in A["逐年"].items():
        d = (v["策略"] - v["^SP500TR"]) * 100
        H.append(f"<tr><td>{e(y)}</td><td class='n'>{pc(v['策略'])}</td><td class='n'>{pc(v['^SP500TR'])}</td><td class='n {'up' if d >= 0 else 'dn'}'>{d:+.1f}</td></tr>")
    H.append("</table></div><h2>b 獲利集中在誰</h2>")
    H.append(f"<p>前 3 檔占總獲利 <b>{pc(B['前3檔占總獲利'], sign=False)}</b>、前 10 檔 <b>{pc(B['前10檔占總獲利'], sign=False)}</b>（交易過 {B['交易過檔數']} 檔）。</p>")
    H.append("<div class='w'><table><tr><th>名次</th><th>代號</th><th>占總獲利</th><th>窗尾仍持有</th></tr>")
    for i, t in enumerate(B["前10檔"], 1):
        H.append(f"<tr><td>{i}</td><td>{e(t['代號'])}</td><td class='n'>{pc(t['占總獲利'], sign=False)}</td><td>{'是' if t['窗尾仍持有'] else '否'}</td></tr>")
    H.append(f"</table></div><p>拿掉前 3 檔、讓下一名補位重跑：年化 <b>{pc(x['年化'])}</b>、回落 {pc(x['回落'])}（^SP500TR {pc(bm['年化'])}）。"
             f"<span class='m'>不重跑、直接扣掉三檔損益：{pc(B['拿掉前3檔（副：權益直接扣損益）']['年化'])}。</span></p>")
    H.append("<h2>c 假訊號：S&amp;P 500 內隨機 8 檔</h2>")
    H.append(f"<p>200 次，換手照主臂抽：年化中位 {pc(F['年化中位'])}（p10 {pc(F['隨機年化 p10'])}～p90 {pc(F['隨機年化 p90'])}）；"
             f"<b>贏 ^SP500TR 的比例 p ＝ {pc(F['p（隨機年化 ＞ ^SP500TR）'], sign=False)}</b>；隨機 ≥ 主臂 {pc(F['隨機年化 ≥ 主臂 的比例'], sign=False)}。</p>")
    H.append("<h2>與 C3「只 S&amp;P 500」欄是否同一算法</h2>")
    H.append(f"<p>{'<b>同一算法</b>：C3 該欄就是先限 S&amp;P 500 再排名，數字逐位相同。' if S2['與本規則同算法'] else '⚠ 不同算法'}"
             f"另報「合併 500∪400 排名後篩 500」：年化 {pc(V['年化'])}、回落 {pc(V['回落'])}（描述；判定照本規則）。</p>")
    H.append("<h2>判定還在等什麼</h2><ul><li>① 早年段 2000～2015：<b>等資料庫</b>（S&amp;P 500 成分延伸到 1999、已下市股還原價；覆蓋率 ≥ 95% 才可判）。</li>"
             "<li>② 前瞻：2026-10 月底起每月記（樣板 forward_template.csv），2029-10 月底第一次判，中途只報不判。</li></ul>")
    H.append("<h2>先驗</h2><ul>" + "".join(f"<li>{e(p['先驗'])}：{e(p['結果'])}（{'對' if p['對'] else ('錯' if p['對'] is False else '—')}）</li>" for p in o["先驗"]) + "</ul>")
    if ck:
        H.append(f"<p class='m'><small>獨立查核 --check：抽樣 {ck['總抽樣']}、不同 {ck['總不同']}。</small></p>")
    H.append(f"<p class='m'><small>{e(o['存活者偏差'])}。逐日權益、逐筆成交不在本頁。</small></p></body></html>")
    open(os.path.join(OUTD, HTMLN), "w", encoding="utf-8").write("\n".join(H))


# ═════════════ --check（S8；獨立寫法）═════════════
def check():
    T0 = time.time()
    R = K.rworld(); W = R["Wd"]; cal = R["cal"]; w1 = R["w1"]; tick = W["tick"]
    C, valid, pb, O = W["C"], W["valid"], W["pb"], W["O"]
    m5 = W["m5"]; nS = C.shape[1]
    S = json.load(open(os.path.join(OUTD, "summary.json"), encoding="utf-8"))
    d = pd.to_datetime(pd.Series(cal)); ymv = (d.dt.year * 12 + d.dt.month - 1).to_numpy()
    lastd, firstd = {}, {}
    for i, k in enumerate(ymv):
        lastd[int(k)] = i; firstd.setdefault(int(k), i)
    CFf = pd.DataFrame(C).ffill().to_numpy()   # 另算 ffill 收盤（計值口徑同 A4 G10）
    reb = [firstd[k] for k in sorted(firstd) if 0 < firstd[k] <= w1 and (k - 13) in lastd]

    def mom_at(e):
        k = int(ymv[e]); a12, a1 = lastd[k - 13], lastd[k - 2]
        sc = np.full(nS, np.nan)
        for j in range(nS):
            if not valid[max(a12 - 4, 0):a12 + 1, j].any() or not valid[max(a1 - 4, 0):a1 + 1, j].any():
                continue
            if pb[a12 + 1:e, j].any():
                continue
            v = CFf[a1, j] / CFf[a12, j] - 1
            if np.isfinite(v):
                sc[j] = v
        return sc

    def lists(e, sc):
        el = [j for j in range(nS) if m5[e - 1, j] and np.isfinite(sc[j])]
        el.sort(key=lambda j: (-sc[j], j))
        k1 = -(-len(el) // 10); k2 = -(-2 * len(el) // 10)
        return el[:k1], el[:k2]

    # 主臂名單（全部換股日，獨立算；X1 抽樣比對）
    LB, LK = {}, {}
    for e in reb:
        sc = mom_at(e); b_, k_ = lists(e, sc)
        if len(b_):
            LB[e], LK[e] = b_, set(k_)
    t0 = min(LB); a0 = t0 - 1
    BUY, KEEP, _ = K.rank_tables(C3.mom_scores(), R["memb"]["只500"])
    rng = np.random.default_rng(20261011)
    samp = sorted(int(x) for x in rng.choice(sorted(LB), size=15, replace=False))
    x1d = sum(int(set(LB[e]) != set(BUY[e]) or LK[e] != KEEP[e]) for e in samp)
    x1 = {"項": "X1 抽 15 個換股日：S&P 500 內 MOM 前 10%／前 20% 名單", "抽樣": len(samp), "不同": x1d}
    # X2 另寫換股簿
    cost = K.COST; Nn = 8
    last_valid = {j: (int(np.flatnonzero(valid[:, j])[-1]) if valid[:, j].any() else -1) for j in range(nS)}
    holds = {}; cash = 1.0; eqv = {}; pending = set(); pn = defaultdict(float); prev = 1.0
    rebset = set(LB)
    for t in range(t0, w1 + 1):
        for j in list(holds):
            h = holds[j]
            if t > h["d"] and pb[t, j]:
                px = CFf[t - 1, j]
            elif t > last_valid[j]:
                px = CFf[last_valid[j], j]
            else:
                continue
            del holds[j]; pending.discard(j)
            cash += h["u"] * px - h["a"] * cost; pn[j] += h["u"] * px - h["a"] * (1 + cost)
        if t in rebset:
            pending = (pending | {j for j in holds if j not in LK[t]}) - LK[t]
        for j in sorted(pending):
            if j not in holds:
                pending.discard(j); continue
            if valid[t, j] and np.isfinite(O[t, j]) and O[t, j] > 0:
                h = holds.pop(j); pending.discard(j)
                cash += h["u"] * O[t, j] - h["a"] * cost; pn[j] += h["u"] * O[t, j] - h["a"] * (1 + cost)
        if t in rebset:
            cand = [j for j in LB[t] if j not in holds][:max(Nn - len(holds), 0)]
            for j in cand:
                if not (valid[t, j] and np.isfinite(O[t, j]) and O[t, j] > 0):
                    continue
                amt = min(prev / Nn, cash)
                if amt <= 1e-12:
                    break
                cash -= amt; holds[j] = {"u": amt / O[t, j], "a": amt, "d": t}
        prev = cash + sum(h["u"] * CFf[t, j] for j, h in holds.items()); eqv[t] = prev
    for j, h in holds.items():
        pn[j] += h["u"] * CFf[w1, j] - h["a"]
    res = K.book(W, sorted(KEEP), KEEP, BUY, 8, t0, w1)
    ds = sorted(int(x) for x in rng.choice(np.arange(t0, w1 + 1), size=40, replace=False)) + [w1]
    x2d = sum(int(abs(eqv[t] - res["eq"][t]) > 1e-9) for t in ds)
    seg = np.array([1.0] + [eqv[t] for t in range(t0, w1 + 1)])
    yrs = (w1 - a0) / 252; ann = seg[-1] ** (1 / yrs) - 1; pk = np.maximum.accumulate(seg); mdd = ((seg - pk) / pk).min()
    x2d += int(abs(ann - S["a 看過段"]["年化"]) > 1e-9) + int(abs(mdd - S["a 看過段"]["回落"]) > 1e-9)
    x2 = {"項": "X2 另寫換股簿：抽 40 日＋窗尾權益、年化、回落", "抽樣": len(ds) + 2, "不同": x2d}
    # X3 每檔損益
    ser = pd.Series(dict(pn)).sort_values(ascending=False)
    tot = seg[-1] - 1
    x3d = 0
    for i, t_ in enumerate(S["b 集中度"]["前10檔"]):
        j = int(ser.index[i])
        x3d += int(str(tick[j]) != t_["代號"] or abs(ser.iloc[i] - t_["損益（1.0 起算）"]) > 1e-9)
    x3d += int(abs(ser.iloc[:3].sum() / tot - S["b 集中度"]["前3檔占總獲利"]) > 1e-9) + int(abs(ser.sum() - tot) > 1e-9)
    x3 = {"項": "X3 另算每檔損益：前 10 檔代號與損益、前 3 檔占比、恆等式", "抽樣": 12, "不同": x3d}
    xs = [x1, x2, x3]
    out = {"件": "USREG-C3s --check（獨立寫法，⛔ 不呼叫 K.book 以外的名單／記帳函式；K.book 只當被比對方）", "項": xs,
           "總抽樣": sum(x["抽樣"] for x in xs), "總不同": sum(x["不同"] for x in xs), "算於": K.now_tpe() + "（台北）", "秒": round(time.time() - T0)}
    jd(out, "check.json")
    K.log("[C3s] check %s" % json.dumps(out, ensure_ascii=False), "c3s.log")
    write_html(S)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--procs", type=int, default=3)
    ap.add_argument("--seeds", type=int, default=K.NSEED)
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    os.makedirs(WORKD, exist_ok=True); os.makedirs(OUTD, exist_ok=True)
    if a.check:
        check()
    else:
        run(a)


if __name__ == "__main__":
    main()

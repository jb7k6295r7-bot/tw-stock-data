# -*- coding: utf-8 -*-
"""大跌 4 檔「分段加碼兩次」描述性測試（⛔ 不計 N、⛔ 不判定、⛔ 不是買賣建議）——回測線計算子代理，2026-10-21。
使用者 10/21：現行 ＝ 大盤比大跌日收盤再跌 5% 時加碼一次（每事件只一次）；想看「−5% 加一次、−10% 再加一次」會怎樣。
⛔ 只計算：不 commit、不 push、不寫跨線信箱、不改既有檔；⛔ 不寫第二份實作 ⇒ researchMktDrop_addon2.run 原樣重跑（輸出改到 ~/mktdropwork/addon3/，
   ⛔ 不動 resultsMktDrop/addon2），攔 curve2_add 取 run 內的世界、逐股矩陣、觸發、F9 名單與加碼路徑；本檔只新增「多次觸發」的合併（combine_multi）與曲線（curve3_add）。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchMktDrop_addon3 --dry      # 乾跑（無任何報酬）
    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchMktDrop_addon3 [--procs 3]

═══ 讀法（寫死於第一次跑之前，2026-10-21 17:15 台北；⚠ 已看過 addon2 的 T2／T3 結果與排名表 ⇒ 事後提問、只描述）═══
 B0 事件、首次進場、出場、成本 ⭐ 全部照 addon2（A0～A3）：V1.index_events q2 接受事件、主世界 2015 起 18 事件（2015～2021 7、2022～ 11）；
    F9 前 4（f9/features.csv 排序）t＋1 開盤等權買；方式乙 ＝ 加碼原本首次買到的同一批（ta＋1 開盤買不到、或首次那份已在 ta＋1 開盤前出場 ⇒ 該檔不加）；
    主出場 ＝ 首次＋加碼全部在「加權收盤 ≥ 第一次大跌前一日收盤」的隔日開盤賣（addon2 主臂 MX["主"]）；壞根強制、同根兩價取低等全同 v1。
    早年（2006～2014）F9 不可算（Q 無早年財報）⇒ 「—」；⇒ 本件不用早年、不涉 reduce_v2。
 B1 比較臂（皆 F9 前 4、乙、主出場）：
    K0 不加碼；K1 只在 −5% 加一次（＝ addon2 T2／乙／主）；K2 只在 −10% 加一次（＝ addon2 T3／乙／主）；
    K3 −5% 加一次、−10% 再加一次（兩次各與首次同額；觸發日 ta 收盤決定、ta＋1 開盤買；−5%、−10% 的觸發日 ＝ addon2 find_triggers 的 T2、T3〔各自第一次觸及〕）
    ★ 同日同時觸及 −5% 與 −10%（跳空）⇒ K3 主值 ＝ 兩份都加（照字面：兩個門檻在同一個收盤都已觸及，ta＋1 開盤一起買兩份）；
       另報 K3s ＝ 同日只加一份（＝ 該事件等同 K1）當描述對照。
 B2 事件層（每事件）：報酬 ＝ 金額加權 ＝（首次淨報酬 ＋ 各加碼份淨報酬）÷ 份數；最大帳面虧損 ＝ 持有期間每日收盤 總市值 ÷ 已投入 − 1 的最低（毛、≥0 記 0）；
    最低帳面損益（以首次金額為 1）＝ 總市值 − 已投入 的最低；持有天數 ＝ 首次買進到最後一份賣完（日曆位置差）。
    ＝ addon2.combine 推廣到多份（combine_multi；一份加碼時與 addon2.combine 逐位元同 ⇒ 對帳）。
    段：2015～2021、2022～、2015～（18 事件）；早年 「—」。報：平均、中位、最差、虧 ＞10% 次數、最大帳面虧損（平均、最差）、最低帳面損益（首次＝1）最差、持有天數（平均、最長）；
    另報「有觸及 −5% 的事件」子集與逐事件表。
 B3 組合層（裁定 seq430 甲口徑延伸）：平時抱 0050（含息）；事件 t＋1 開盤撥 20%（＝ V1.curve2）；−5% 觸發 ta＋1 開盤再撥「前一日收盤總資產」20%；
    −10% 觸發再撥 20%（上限 60%）；同日兩個都觸發 ⇒ 兩筆都以同一個「前一日收盤總資產」為基準各撥 20%；成本 個股 0.585%、0050 0.385%（撥出、換回皆扣，同 addon2）；
    各部位賣完那一刻換回 0050；首次部位被略過（重疊）的事件不加碼。＝ addon2.curve2_add 推廣到多個加碼部位（curve3_add；一個加碼部位時逐位元同 ⇒ 對帳）。
    窗：確認 2022-01-03～2026-08-24、探索 2017-03-02～2021-12-30（＝ resultsBenchRejudge 排名表窗、benchmark_rejudge.estat／seg_pos 同式）；另報 addon2 原段（V1.wstats）供對帳。
    對照：大盤報酬指數（git:origin/main:data/history/market_tri.csv，benchmark_rejudge.bstat 同式、不含成本）、0050（還原收盤、不含成本）。
 B4 必附：事件少（−10% 只 3 次）、事後提問、F9 為事後選法、加碼越多虧損放大、描述不是買賣建議。
 B5 對帳（不過 ⇒ 停）：addon2 重跑輸出 ＝ resultsMktDrop/addon2 原檔（逐位元：event_rows／summary／portfolio／triggers／trigger_counts）；
    K1、K2 逐事件（報酬、最大帳面虧損、最低帳面損益、持有天數、加碼份報酬）＝ addon2 run 內 EROWS（==）＝ 原 event_rows.csv（%.8g 字串）；
    K0 ＝ EROWS 不加碼欄；曲線 K0、K1、K2 ＝ addon2 curve2_add 攔到的曲線（array_equal）；K0、K1 ＝ resultsBenchRejudge/mktdrop_curves.npz（array_equal）；
    K0、K1 兩窗 年化／回落 ＝ rank.csv；大盤、0050 兩窗 ＝ rank.csv；原段 K1、K2 ＝ addon2/portfolio.csv（%.6g）。
 B6 乾跑（--dry，seq366／seq377）：只算指數觸發（無個股報酬）與合成資料 fixture（combine_multi ≡ addon2.combine、curve3_add ≡ addon2.curve2_add）、條件等價檢查
    （K3 的加碼日集合 ≠ K1、≠ K2 才正式跑）；⛔ 不讀、不算任何個股或組合報酬。
輸出 backtest/resultsMktDrop_addon3/：MktDrop_addon3.json、event_rows.csv、summary.csv、portfolio.csv、curves.npz、triggers.csv、recon.csv、dry.json、run.log
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time

import numpy as np
import pandas as pd

REPO = os.path.expanduser("~/tw-p17")
sys.path.insert(0, REPO)
OUT = os.path.join(REPO, "backtest/resultsMktDrop_addon3")
WORK = os.path.expanduser("~/mktdropwork/addon3")
AD2OUT = os.path.join(REPO, "backtest/resultsMktDrop/addon2")
AD2WORK = os.path.expanduser("~/mktdropwork/addon2")
BRDIR = os.path.join(REPO, "backtest/resultsBenchRejudge")
TIME = "2026-10-21 17:15（台北；讀法寫死、第一次跑之前）"
TRSRC = "git:origin/main:data/history/market_tri.csv"
KS = ["K0", "K1", "K2", "K3", "K3s"]
KN = {"K0": "不加碼", "K1": "只在 −5% 加一次（現行）", "K2": "只在 −10% 加一次", "K3": "−5% 加一次、−10% 再加一次（同日兩份）",
      "K3s": "−5%、−10%（同日只加一份；描述對照）"}
KTRIG = {"K0": (), "K1": ("T2",), "K2": ("T3",), "K3": ("T2", "T3"), "K3s": ("T2", "T3")}
SEGS = ["2015～2021", "2022～", "2015～"]
RANKW = {"確認": ("2022-01-03", "2026-08-24"), "探索": ("2017-03-02", "2021-12-30")}
NOTES = ["描述性測試：⛔ 不計 N、⛔ 不判定、⛔ 不是買賣建議",
         "⚠ 事件少：2015 起 18 個大跌事件，觸及 −5% 的 4 次、觸及 −10% 的 3 次（其中 1 次與 −5% 同一天跳空）⇒ 差異幾乎全由這 3～4 次決定",
         "⚠ 事後提問：addon2 的 −5%／−10% 單次加碼結果與排名表都已看過，「兩次都加」是看過之後才問的",
         "⚠ F9 前 4 是事後選法（使用者採用、未驗證）",
         "⚠ 加碼越多、同一波下跌押得越重：收復前的帳面虧損放大（以首次金額為 1 時更明顯）；收復才賣的勝率有一部分來自規則本身（等多久都等）",
         "早年（2006～2014）F9 不可算（Q 沒有早年財報）⇒ 「—」；本件不用早年資料、不涉 reduce_v2 減資註",
         "成本：個股 0.585% 來回、0050 0.385%（撥出、換回皆扣）；未含滑價；最大帳面虧損為毛值（未扣成本）；大盤、0050 基準不含成本"]


def now_tpe():
    return pd.Timestamp.now(tz="Asia/Taipei").strftime("%Y-%m-%d %H:%M")


# ═════════════ 新增：多份合併（addon2.combine 推廣）═════════════
def combine_multi(V1_, e1, end1, adds):
    """V1_：(D, L1) 首次毛值路徑；adds：[(V2_ (D, L2), e2, end2 (D,)), …]（依加碼先後）。
    ⇒ (最大帳面虧損 相對已投入, 最低帳面損益 以首次為 1, 持有天數)，各 (D,)。adds 空 ⇒ ＝ addon2.combine(…, None)；一份 ⇒ 與 addon2.combine 逐位元同。"""
    from backtest import researchMktDrop_addon2 as AD
    if not adds:
        return AD.combine(V1_, e1, end1, None, None, None)
    D_ = V1_.shape[0]
    L = max([e1 + V1_.shape[1]] + [e2 + V2_.shape[1] for V2_, e2, _ in adds]) - e1
    v1 = np.empty((D_, L)); v1[:, :V1_.shape[1]] = V1_; v1[:, V1_.shape[1]:] = V1_[:, -1:]
    inv = np.ones(L); tot = v1; endm = end1
    for V2_, e2, end2 in adds:
        v2 = np.zeros((D_, L)); o2 = e2 - e1
        v2[:, o2:o2 + V2_.shape[1]] = V2_; v2[:, o2 + V2_.shape[1]:] = V2_[:, -1:]
        inv[o2:] += 1.0
        tot = tot + v2
        endm = np.maximum(endm, end2)
    rel = np.minimum(0.0, np.nanmin(tot / inv - 1.0, axis=1)); ab = np.minimum(0.0, np.nanmin(tot - inv, axis=1))
    return rel, ab, (endm - e1).astype(float)


# ═════════════ 新增：多個加碼部位的組合曲線（addon2.curve2_add 推廣）═════════════
def curve3_add(n0, paths, addps, BO, BC, cost):
    """addps：[addp_1, addp_2, …]（addp ＝ {首次進場位置 e0: (ea, end, V, reopen)}，同 addon2）；每個 addp 是一個加碼槽（同時最多一個部位）。
    加碼日先算一次「前一日收盤總資產」（0050＋首次部位＋已在場的加碼部位），同日多筆都以它為基準各撥 W_ADD。
    ⇒ (淨值曲線, 略過事件數, 加碼略過數, 加碼次數, 部位最大占比)。addps ＝ [addp] ⇒ 與 addon2.curve2_add 逐位元同；[] ⇒ ＝ V1.curve2。"""
    from backtest import researchMktDrop_addon2 as AD
    W_SLEEVE, W_ADD, COST_ETF = AD.W_SLEEVE, AD.W_ADD, AD.COST_ETF
    by_e = {p[0]: p for p in paths}
    by_a = {}
    for kk, addp in enumerate(addps):
        for e0, pa in addp.items():
            by_a.setdefault(pa[0], []).append((kk, e0, pa))
    eq = np.ones(n0); core = 1.0; act = None; acts = {}; skipped = 0; skipped2 = 0; added = 0; wmax = 0.0
    for j in range(1, n0):
        o_ = BO[j] if np.isfinite(BO[j]) and BO[j] > 0 else BC[j - 1]
        core *= o_ / BC[j - 1]
        prevA = 0.0
        for kk in sorted(acts):
            a2 = acts[kk]
            if j - 1 >= a2[0]:
                prevA += a2[4] * a2[2][j - 1 - a2[0]]
        if j in by_e:
            if act is None:
                e0, end, V, reopen = by_e[j]
                tot = core + prevA; core = tot * (1 - W_SLEEVE) - prevA
                act = (e0, end, V, reopen, tot * W_SLEEVE * (1 - cost) * (1 - COST_ETF))
            else:
                skipped += 1
        if j in by_a:
            tot = None
            for kk, e0p, (ea, end, V, reopen) in by_a[j]:
                if act is not None and act[0] == e0p and kk not in acts:
                    if tot is None:
                        prev1 = act[4] * act[2][j - 1 - act[0]] if j - 1 >= act[0] else 0.0
                        tot = core + prev1 + prevA
                    core = core - tot * W_ADD
                    acts[kk] = (ea, end, V, reopen, tot * W_ADD * (1 - cost) * (1 - COST_ETF)); added += 1
                else:
                    skipped2 += 1
        sl = 0.0
        if act is not None:
            e0, end, V, reopen, S0 = act
            if j == end and reopen:
                core += S0 * V[j - e0]
        for kk in sorted(acts):
            ea, end2, V2, reopen2, S2 = acts[kk]
            if j == end2 and reopen2:
                core += S2 * V2[j - ea]
        core *= BC[j] / o_
        if act is not None:
            e0, end, V, reopen, S0 = act
            if j == end:
                if not reopen:
                    core += S0 * V[j - e0]
                act = None
            else:
                sl = S0 * V[j - e0]
        for kk in sorted(acts):
            ea, end2, V2, reopen2, S2 = acts[kk]
            if j == end2:
                if not reopen2:
                    core += S2 * V2[j - ea]
                del acts[kk]
            else:
                sl += S2 * V2[j - ea]
        eq[j] = core + sl
        if sl > 0:
            wmax = max(wmax, sl / eq[j])
    return eq, skipped, skipped2, added, wmax


# ═════════════ 乾跑：指數觸發＋合成 fixture（⛔ 無任何個股或組合報酬）═════════════
def dry(log):
    from backtest import researchMktDrop as MD
    from backtest import researchMktDrop_v1 as V1
    from backtest import researchMktDrop_addon2 as AD
    J = {"件": "大跌 4 檔 分段加碼兩次｜乾跑（無報酬）", "時間（台北）": now_tpe()}
    IXmd = MD.load_index(log); df = IXmd["df"]; EV = V1.index_events(df)
    TRG = AD.find_triggers(EV, df)
    rows = []
    for i0, T in sorted(TRG.items()):
        d = df["date"].iloc[i0]
        if d < pd.Timestamp("2015-01-01"):
            continue
        r = {"事件日": str(d.date())}
        for k in ("T2", "T3"):
            r[k] = None if T[k] is None else str(df["date"].iloc[T[k]].date())
        r["同日"] = bool(r["T2"] is not None and r["T2"] == r["T3"])
        rows.append(r)
    TR0 = pd.read_csv(os.path.join(AD2OUT, "triggers.csv")); TR0 = TR0[TR0["世界"] == "主"]
    J["指數新事件（不在 addon2 主世界日曆內 ⇒ 不在本件）"] = [r for r in rows if r["事件日"] not in set(TR0["事件日"])]
    rows = [r for r in rows if r["事件日"] in set(TR0["事件日"])]
    same = all(str(TR0.set_index("事件日").loc[r["事件日"], k]) == str(r[k]) if r[k] is not None else pd.isna(TR0.set_index("事件日").loc[r["事件日"], k])
               for r in rows for k in ("T2", "T3"))
    J["2015 起事件數"] = len(rows); J["觸發 ＝ addon2/triggers.csv"] = bool(same and len(rows) == len(TR0))
    J["−5% 觸發"] = [(r["事件日"], r["T2"]) for r in rows if r["T2"]]; J["−10% 觸發"] = [(r["事件日"], r["T3"]) for r in rows if r["T3"]]
    J["同日跳空"] = [(r["事件日"], r["T2"]) for r in rows if r["同日"]]
    S1 = {(r["事件日"], "T2", r["T2"]) for r in rows if r["T2"]}; S2 = {(r["事件日"], "T3", r["T3"]) for r in rows if r["T3"]}
    S3s = S1 | {x for x in S2 if (x[0], "T2", x[2]) not in S1}
    neq = (S1 | S2 != S1) and (S1 | S2 != S2)
    J["條件等價檢查（seq377）"] = {"K3 加碼集合 ＝ K1": S1 | S2 == S1, "K3 加碼集合 ＝ K2": S1 | S2 == S2, "K3s 加碼集合 ＝ K1": S3s == S1,
                              "結論": "不等價 ⇒ 正式跑" if neq else "⚠ 等價 ⇒ 先回信、不正式跑"}
    # 合成 fixture（亂數，非真實資料）
    rng = np.random.default_rng(20261021)
    bad = 0
    for _ in range(300):
        L1 = int(rng.integers(3, 40)); V1_ = 1 + np.cumsum(rng.normal(0, 0.02, (1, L1)), axis=1); e1 = int(rng.integers(0, 50))
        o2 = int(rng.integers(1, L1 + 5)); L2 = int(rng.integers(1, 40)); V2_ = 1 + np.cumsum(rng.normal(0, 0.02, (1, L2)), axis=1)
        end1 = np.array([e1 + L1 - 1]); end2 = np.array([e1 + o2 + L2 - 1])
        a = AD.combine(V1_, e1, end1, V2_, e1 + o2, end2); b = combine_multi(V1_, e1, end1, [(V2_, e1 + o2, end2)])
        bad += int(not all(np.array_equal(x, y) for x, y in zip(a, b)))
        a = AD.combine(V1_, e1, end1, None, None, None); b = combine_multi(V1_, e1, end1, [])
        bad += int(not all(np.array_equal(x, y) for x, y in zip(a, b)))
    J["fixture combine_multi ≡ addon2.combine（300 組×2）不符"] = bad
    bad = 0; badw = 0
    for it in range(60):
        n0 = 400; BC = 50 * np.exp(np.cumsum(rng.normal(0, 0.01, n0))); BO = BC * np.exp(rng.normal(0, 0.003, n0)); BO[rng.random(n0) < 0.02] = np.nan
        paths = []; addA = {}; addB = {}; j = 5
        while j < n0 - 60:
            L = int(rng.integers(5, 50)); V = 1 + np.cumsum(rng.normal(0, 0.02, L)); paths.append((j, j + L - 1, V, bool(rng.random() < 0.5)))
            if rng.random() < 0.6:
                ea = j + int(rng.integers(1, L)); addA[j] = (ea, j + L - 1, 1 + np.cumsum(rng.normal(0, 0.02, j + L - ea)), paths[-1][3])
                if rng.random() < 0.7:
                    eb = ea + int(rng.integers(0, max(1, j + L - ea - 1))); addB[j] = (eb, j + L - 1, 1 + np.cumsum(rng.normal(0, 0.02, j + L - eb)), paths[-1][3])
            j += L + int(rng.integers(-3, 30))
        a = AD.curve2_add(n0, paths, addA, BO, BC, 0.00585); b = curve3_add(n0, paths, [addA], BO, BC, 0.00585)
        bad += int(not (np.array_equal(a[0], b[0]) and a[1:4] == b[1:4]))
        a = AD.curve2_add(n0, paths, addB, BO, BC, 0.00585); b = curve3_add(n0, paths, [addB], BO, BC, 0.00585)
        bad += int(not (np.array_equal(a[0], b[0]) and a[1:4] == b[1:4]))
        a = V1.curve2(n0, paths, BO, BC, 0.00585); b = curve3_add(n0, paths, [], BO, BC, 0.00585)
        bad += int(not np.array_equal(a[0], b[0]))
        c = curve3_add(n0, paths, [addA, addB], BO, BC, 0.00585)
        badw += int(c[4] > 0.60 + 0.05)
    J["fixture curve3_add ≡ addon2.curve2_add／V1.curve2（60 組×3）不符"] = bad
    J["fixture 兩槽部位占比 ＞ 65%（粗檢）"] = badw
    log(json.dumps(J, ensure_ascii=False, indent=1))
    json.dump(J, open(os.path.join(OUT, "dry.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    if bad or not J["觸發 ＝ addon2/triggers.csv"] or not neq or J["fixture combine_multi ≡ addon2.combine（300 組×2）不符"]:
        raise SystemExit("⛔ 乾跑不過")


# ═════════════ 正式跑 ═════════════
def run(a, log):
    T0 = time.time()
    from backtest import researchMktDrop_addon2 as AD
    from backtest import researchMktDrop_v1 as V1
    from backtest import researchMktDrop_f9 as F9
    from backtest import researchAddOn as RA
    from backtest import benchmark_rejudge as BR
    S = {"件": "大跌 4 檔 分段加碼兩次（描述性、不計 N、不判定）", "讀法寫死": TIME, "開跑（台北）": now_tpe(), "讀法": "見程式檔頭 B0～B6", "必附": NOTES, "臂": KN, "對帳": {}}
    REC = []

    def rec(name, val, ok, note=""):
        REC.append({"對帳": name, "值": str(val), "通過": bool(ok), "註": note}); log(f"[對帳] {name}：{val}｜{'✔' if ok else '✘'} {note}")
        if not ok:
            pd.DataFrame(REC).to_csv(os.path.join(OUT, "recon.csv"), index=False, encoding="utf-8")
            raise SystemExit(f"⛔ 對帳不過：{name} {val}")

    lk = subprocess.run([sys.executable, "-m", "backtest.strategy_lock", "--check"], capture_output=True, text=True, cwd=REPO)
    rec("策略鎖（開跑前）", lk.stdout.strip(), lk.returncode == 0 and "25 支" in lk.stdout)
    # ── addon2 原樣重跑（輸出改道）＋ 攔 curve2_add ──
    o2, w2 = os.path.join(WORK, "addon2_rerun_out"), os.path.join(WORK, "addon2_rerun_work")
    os.makedirs(o2, exist_ok=True); os.makedirs(w2, exist_ok=True)
    for f in ("f9_features.pkl", "f9_features_v2.pkl"):
        if os.path.exists(os.path.join(AD2WORK, f)) and not os.path.exists(os.path.join(w2, f)):
            shutil.copy(os.path.join(AD2WORK, f), w2)
    AD.OUT, AD.WORK = o2, w2
    CAP = {}; CTX = {}
    orig = AD.curve2_add

    def wrap(n0, paths, addp, BO, BC, cost):
        r = orig(n0, paths, addp, BO, BC, cost)
        L = sys._getframe(1).f_locals
        if L.get("cd") == "F9" and L.get("wn") == "主":
            pp = L.get("PP")
            key = (L["k"], L["mt"], L["arm"]) if (pp is not None and pp.get("add") is addp) else ("不加碼", "", "")
            CAP[key] = r
            if not CTX:
                for nm in ("W", "M", "MX", "TW", "evs", "F9F", "rix", "PATHS", "EROWS", "segof", "base_paths", "BO", "BC", "n0", "cost"):
                    CTX[nm] = L[nm]
        return r
    AD.curve2_add = wrap
    try:
        AD.run(a, RA.log_to(os.path.join(o2, "run.log")))
    finally:
        AD.curve2_add = orig
    for f in ("event_rows.csv", "summary.csv", "portfolio.csv", "triggers.csv", "trigger_counts.csv", "addon_list.csv", "concentration.csv"):
        same = open(os.path.join(o2, f), "rb").read() == open(os.path.join(AD2OUT, f), "rb").read()
        rec(f"addon2 重跑 {f} ＝ resultsMktDrop/addon2 原檔（逐位元）", same, same)
    W, M, MX, TW, evs, F9F, rix, PATHS, EROWS = (CTX[k] for k in ("W", "M", "MX", "TW", "evs", "F9F", "rix", "PATHS", "EROWS"))
    segof = CTX["segof"]; base_paths = CTX["base_paths"]; BO, BC, n0, cost = CTX["BO"], CTX["BC"], CTX["n0"], CTX["cost"]
    cal = W["cal"]
    # ── 事件層 ──
    ER = {(r["事件日"], r["觸發"]): r for r in EROWS if r["世界"] == "主" and r["候選"] == "F9" and r["方式"] == "乙" and r["出場"] == "主"}
    ROWS = []; TRROWS = []
    nchk = 0
    for p, i in evs:
        ds = str(cal[p].date()); sg = segof(p)
        d9 = F9F[F9F["事件日"] == ds]
        top = F9.order(d9, "F9").head(AD.N4)["sid"].tolist()
        rr_ = np.array([rix[s] for s in top], int); I1 = rr_[M["BUY"][rr_, p]]
        if len(I1):
            P1, e1, end1, sp1, kd1, g1 = AD.spath(W, M, I1, p)
            V1_ = np.nanmean(P1, axis=0)[None, :]
            net1 = (1 + float(np.mean(g1))) * (1 - cost) - 1
        else:
            V1_ = None; net1 = 0.0; e1 = p + 1; end1 = p + 1
        AJ = {}
        for k in ("T2", "T3"):
            pa = TW[p][k]
            if pa is None or isinstance(pa, str) or not len(I1):
                continue
            held = (2 * M["SP"]["主"][I1, p].astype(np.int64) + (M["SK"]["主"][I1, p] != 0)) > 2 * (pa + 1)
            I2 = I1[held & M["BUY"][I1, pa]]
            if not len(I2):
                continue
            P2, e2, end2, sp2, kd2, g2 = AD.spath(W, MX["主"], I2, pa)
            AJ[k] = {"pa": pa, "V": np.nanmean(P2, axis=0)[None, :], "e2": e2, "end2": np.array([end2]), "net": (1 + float(np.mean(g2))) * (1 - cost) - 1,
                     "n": int(len(I2)), "hd": float(end2 - e2)}
        TRROWS.append({"段": sg, "事件日": ds, "F9前4": " ".join(top), "首次買到檔數": int(len(I1)),
                       "−5%觸發日": (None if TW[p]["T2"] is None else str(cal[TW[p]["T2"]].date())), "−10%觸發日": (None if TW[p]["T3"] is None else str(cal[TW[p]["T3"]].date())),
                       "同日跳空": bool(TW[p]["T2"] is not None and TW[p]["T2"] == TW[p]["T3"]),
                       "−5%加碼檔數": AJ.get("T2", {}).get("n", 0), "−10%加碼檔數": AJ.get("T3", {}).get("n", 0)})
        for K in KS:
            ks = [k for k in KTRIG[K] if k in AJ]
            if K == "K3s" and "T2" in AJ and "T3" in AJ and AJ["T2"]["pa"] == AJ["T3"]["pa"]:
                ks = ["T2"]
            row = {"段": sg, "事件日": ds, "臂": K, "加碼份數": len(ks), "加碼日": " ".join(str(cal[AJ[k]["pa"] + 1].date()) for k in ks)}
            if V1_ is None:
                row.update({"報酬": 0.0, "最大帳面虧損": 0.0, "最低帳面損益（首次＝1）": 0.0, "持有天數": 0.0, "首次份報酬": 0.0})
            else:
                mn, ab, hd = combine_multi(V1_, e1, np.array([end1]), [(AJ[k]["V"], AJ[k]["e2"], AJ[k]["end2"]) for k in ks])
                s_ = net1
                for k in ks:
                    s_ = s_ + AJ[k]["net"]
                comb = s_ / (1 + len(ks)) if ks else net1
                row.update({"報酬": comb, "最大帳面虧損": float(mn[0]), "最低帳面損益（首次＝1）": float(ab[0]), "持有天數": float(hd[0]), "首次份報酬": net1})
            for k, nm in (("T2", "−5%份"), ("T3", "−10%份")):
                row[f"{nm}報酬"] = AJ[k]["net"] if k in ks else np.nan
            ROWS.append(row)
            # 對帳：K0／K1／K2 ＝ addon2 run 內 EROWS（==）
            if K in ("K0", "K1", "K2"):
                ref = ER[(ds, {"K0": "T2", "K1": "T2", "K2": "T3"}[K])]
                if K == "K0":
                    pairs = [(row["報酬"], ref["不加碼_報酬"]), (row["最大帳面虧損"], ref["不加碼_最大帳面虧損"]), (row["持有天數"], ref["不加碼_持有天數"])]
                else:
                    pairs = [(row["報酬"], ref["加碼後_報酬"]), (row["最大帳面虧損"], ref["加碼後_最大帳面虧損"]),
                             (row["最低帳面損益（首次＝1）"], ref["加碼後_最低帳面損益（首次＝1）"]), (row["持有天數"], ref["加碼後_持有天數"])]
                    if ks:
                        pairs.append((AJ[ks[0]]["net"], ref["加碼份_報酬"]))
                    if bool(ks) != bool(ref.get("加碼進場")):
                        pairs.append((0.0, 1.0))
                nchk += 1
                if not all(x == y for x, y in pairs):
                    rec(f"{K} {ds} ＝ addon2 EROWS", pairs, False)
    rec(f"K0／K1／K2 逐事件 ＝ addon2 run 內 EROWS（==；{nchk} 列）", "全同", True)
    E0 = pd.read_csv(os.path.join(AD2OUT, "event_rows.csv"), dtype=str)
    E0 = E0[(E0["世界"] == "主") & (E0["候選"] == "F9") & (E0["方式"] == "乙") & (E0["出場"] == "主")]
    badf = 0
    for r in ROWS:
        if r["臂"] not in ("K1", "K2"):
            continue
        q = E0[(E0["事件日"] == r["事件日"]) & (E0["觸發"] == ("T2" if r["臂"] == "K1" else "T3"))].iloc[0]
        for c_, rc_ in (("報酬", "加碼後_報酬"), ("最大帳面虧損", "加碼後_最大帳面虧損"), ("最低帳面損益（首次＝1）", "加碼後_最低帳面損益（首次＝1）"), ("持有天數", "加碼後_持有天數")):
            badf += int("%.8g" % r[c_] != q[rc_])
    rec("K1／K2 逐事件 ＝ addon2/event_rows.csv 原檔（%.8g 字串；36 列×4 欄）", badf, badf == 0)
    EV = pd.DataFrame(ROWS); EV.to_csv(os.path.join(OUT, "event_rows.csv"), index=False, float_format="%.8g", encoding="utf-8")
    TRD = pd.DataFrame(TRROWS); TRD.to_csv(os.path.join(OUT, "triggers.csv"), index=False, encoding="utf-8")
    # 事件層彙總
    SUM = []
    trig_ev = set(TRD.loc[TRD["−5%觸發日"].notna(), "事件日"])
    for K in KS:
        for sub in ("全部事件", "觸及 −5% 的事件"):
            for sg in SEGS:
                q = EV[EV["臂"] == K]
                q = q if sg == "2015～" else q[q["段"] == sg]
                if sub != "全部事件":
                    q = q[q["事件日"].isin(trig_ev)]
                r_ = q["報酬"].to_numpy(float)
                SUM.append({"臂": K, "名稱": KN[K], "子集": sub, "段": sg, "事件數": len(q),
                            "−5%加碼次數": int(q["−5%份報酬"].notna().sum()), "−10%加碼次數": int(q["−10%份報酬"].notna().sum()),
                            "平均": float(r_.mean()) if len(r_) else np.nan, "中位": float(np.median(r_)) if len(r_) else np.nan,
                            "最差": float(r_.min()) if len(r_) else np.nan, "虧＞10%次數": int((r_ < -0.10).sum()),
                            "最大帳面虧損_平均": float(q["最大帳面虧損"].mean()) if len(q) else np.nan, "最大帳面虧損_最差": float(q["最大帳面虧損"].min()) if len(q) else np.nan,
                            "最低帳面損益（首次＝1）_最差": float(q["最低帳面損益（首次＝1）"].min()) if len(q) else np.nan,
                            "持有天數_平均": float(q["持有天數"].mean()) if len(q) else np.nan, "持有天數_最長": float(q["持有天數"].max()) if len(q) else np.nan})
        SUM.append({"臂": K, "名稱": KN[K], "子集": "全部事件", "段": "2006～2014", "事件數": "—", "備註": "早年 F9 不可算（Q 無早年財報）"})
    SUM = pd.DataFrame(SUM); SUM.to_csv(os.path.join(OUT, "summary.csv"), index=False, float_format="%.6g", encoding="utf-8")
    # ── 組合層 ──
    ADD = {k: PATHS.get(("F9", k, "乙", "主"), {"add": {}})["add"] for k in ("T2", "T3")}
    same_e = {e0 for e0, v in ADD["T3"].items() if e0 in ADD["T2"] and ADD["T2"][e0][0] == v[0]}
    ADDP = {"K0": [], "K1": [ADD["T2"]], "K2": [ADD["T3"]], "K3": [ADD["T2"], ADD["T3"]],
            "K3s": [ADD["T2"], {e0: v for e0, v in ADD["T3"].items() if e0 not in same_e}]}
    # 加碼路徑 ＝ 本檔逐事件重算（同一批、主臂）：起點／終點一致
    for k in ("T2", "T3"):
        mine = {r_["事件日"] for r_ in ROWS if r_["臂"] == ("K1" if k == "T2" else "K2") and r_["加碼份數"]}
        theirs = {str(cal[e0 - 1].date()) for e0 in ADD[k]}
        rec(f"組合層 {k} 加碼事件 ＝ 事件層有加碼事件", f"{sorted(theirs)}", mine == theirs)
    CUR = {}; INFO = {}
    for K in KS:
        eq, s1, s2, ad, wm = curve3_add(n0, base_paths, ADDP[K], BO, BC, cost)
        CUR[K] = eq; INFO[K] = {"略過事件": s1, "加碼略過": s2, "加碼筆數": ad, "部位最大占比": wm}
    rec("曲線 K0 ＝ addon2 攔到（不加碼）", "array_equal", np.array_equal(CUR["K0"], CAP[("不加碼", "", "")][0]))
    rec("曲線 K1 ＝ addon2 攔到（T2 乙 主）", "array_equal", np.array_equal(CUR["K1"], CAP[("T2", "乙", "主")][0]))
    rec("曲線 K2 ＝ addon2 攔到（T3 乙 主）", "array_equal", np.array_equal(CUR["K2"], CAP[("T3", "乙", "主")][0]))
    Z = np.load(os.path.join(BRDIR, "mktdrop_curves.npz"))
    zd = list(Z["dates"]); md = [str(pd.Timestamp(d).date()) for d in cal]
    rec("曲線 K0／K1 ＝ resultsBenchRejudge/mktdrop_curves.npz 甲_不加碼／甲_T2加碼同一批", "array_equal",
        zd == md and np.array_equal(CUR["K0"], Z["甲_不加碼"]) and np.array_equal(CUR["K1"], Z["甲_T2加碼同一批"]))
    np.savez_compressed(os.path.join(OUT, "curves.npz"), dates=np.array(md), **CUR)
    PORT = []
    P0 = pd.read_csv(os.path.join(AD2OUT, "portfolio.csv"), dtype=str)
    for sg, (x0, y0) in W["segp"].items():
        for K in KS:
            s_ = V1.wstats(CUR[K], x0, y0)
            PORT.append({"窗": f"addon2 原段 {sg}", "起": str(cal[x0].date()), "迄": str(cal[y0].date()), "策略": f"{K} {KN[K]}", "年化": s_["年化"], "最大回落": s_["最大回落"], "比值": s_["比值"]})
            if K in ("K1", "K2"):
                q = P0[(P0["世界"] == "主") & (P0["段"] == sg) & (P0["候選"] == "F9") & (P0["觸發"] == {"K1": "T2", "K2": "T3"}[K]) & (P0["方式"] == "乙") & (P0["出場"] == "主")].iloc[0]
                rec(f"原段 {sg} {K} ＝ addon2/portfolio.csv（%.6g）", ("%.6g" % s_["年化"], "%.6g" % s_["最大回落"]),
                    "%.6g" % s_["年化"] == q["②年化"] and "%.6g" % s_["最大回落"] == q["②最大回落"])
    RK = pd.read_csv(os.path.join(BRDIR, "rank.csv"), dtype=str)
    wcal = BR.world_cal(BR.WORLD_DATA["主"])
    TR = BR.read_series(TRSRC); arrT, nfill = BR.on_cal(TR, wcal)
    b50 = BR.bench0050(BR.WORLD_DATA["主"]); arr50, _ = BR.on_cal(b50, wcal)
    for wnm, (a_, b_) in RANKW.items():
        x, y = BR.seg_pos(wcal, a_, b_)
        bt = BR.bstat(wcal, arrT, x, y); b5 = BR.bstat(wcal, arr50, x, y)
        for nm, c_, m_ in (("大盤（報酬指數）", bt["cagr"], bt["mdd"]), ("0050", b5["cagr"], b5["mdd"])):
            q = RK[(RK["段"] == wnm) & (RK["策略"] == nm)].iloc[0]
            rec(f"{wnm} {nm} ＝ rank.csv", (c_, m_), abs(c_ - float(q["年化"])) < 1e-9 and abs(m_ - float(q["回落"])) < 1e-9)
        for K in KS:
            e_ = pd.Series(CUR[K], index=pd.to_datetime(md)).reindex(wcal).to_numpy(float)
            c_, m_ = BR.estat(e_, x, y)
            rt = c_ / abs(m_)
            if K in ("K0", "K1"):
                nm = "大跌 4 檔（甲：撥 20%、不加碼）" if K == "K0" else "大跌 4 檔（甲：撥 20%、−5% 加碼同一批）"
                q = RK[(RK["段"] == wnm) & (RK["策略"] == nm)].iloc[0]
                rec(f"{wnm} {K} ＝ rank.csv「{nm}」", (c_, m_), abs(c_ - float(q["年化"])) < 1e-9 and abs(m_ - float(q["回落"])) < 1e-9)
            PORT.append({"窗": f"排名表 {wnm}", "起": str(wcal[x].date()), "迄": str(wcal[y].date()), "策略": f"{K} {KN[K]}", "年化": c_, "最大回落": m_, "比值": rt,
                         "年化差（−大盤）": c_ - bt["cagr"], "比值差（−大盤）": rt - bt["ratio"], "年化差（−0050）": c_ - b5["cagr"], "比值差（−0050）": rt - b5["ratio"],
                         "窗內事件數": int(sum(1 for pth in base_paths if x <= pth[0] - 1 <= y)),
                         "窗內加碼筆數": int(sum(1 for ad_ in ADDP[K] for e0, v in ad_.items() if x <= v[0] - 1 <= y))})
        for nm, s_ in (("大盤（報酬指數）", bt), ("0050", b5)):
            PORT.append({"窗": f"排名表 {wnm}", "起": str(wcal[x].date()), "迄": str(wcal[y].date()), "策略": nm, "年化": s_["cagr"], "最大回落": s_["mdd"], "比值": s_["ratio"],
                         "備註": "不含成本"})
    PO = pd.DataFrame(PORT); PO.to_csv(os.path.join(OUT, "portfolio.csv"), index=False, float_format="%.6g", encoding="utf-8")
    lk = subprocess.run([sys.executable, "-m", "backtest.strategy_lock", "--check"], capture_output=True, text=True, cwd=REPO)
    rec("策略鎖（結束）", lk.stdout.strip(), lk.returncode == 0 and "25 支" in lk.stdout)
    RC = pd.DataFrame(REC); RC.to_csv(os.path.join(OUT, "recon.csv"), index=False, encoding="utf-8")
    S["曲線資訊"] = INFO; S["同日跳空事件"] = [str(cal[e0 - 1].date()) for e0 in sorted(same_e)]
    S["結束（台北）"] = now_tpe(); S["耗時秒"] = round(time.time() - T0)
    json.dump(S, open(os.path.join(OUT, "MktDrop_addon3.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    pd.set_option("display.width", 260); pd.set_option("display.max_columns", 40); pd.set_option("display.max_rows", 400)
    log("[觸發]\n" + TRD.to_string(index=False))
    log("[事件層]\n" + SUM.to_string(index=False, float_format=lambda v: f"{v:.4f}"))
    log("[逐事件（觸及 −5%）]\n" + EV[EV["事件日"].isin(trig_ev)].to_string(index=False, float_format=lambda v: f"{v:.4f}"))
    log("[組合層]\n" + PO.to_string(index=False, float_format=lambda v: f"{v:.4f}"))
    log(f"[曲線資訊] {INFO}")
    log(f"[完] {S['耗時秒']}s")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--procs", type=int, default=3)
    ap.add_argument("--dry", action="store_true")
    a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True); os.makedirs(WORK, exist_ok=True)
    from backtest import researchAddOn as RA
    log = RA.log_to(os.path.join(OUT, "dry.log" if a.dry else "run.log"))
    if a.dry:
        dry(log)
    else:
        run(a, log)


if __name__ == "__main__":
    main()

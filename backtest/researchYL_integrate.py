# -*- coding: utf-8 -*-
"""PREREG營收趨勢整合 seq1（台股策略線 登錄 sha 71cd40fb9ac104e1；裁定 seq282 §三發號，N_組合 ＋1）＋ 裁定 seq282 §一 早年 IFRS 換軌敏感度（描述）——回測線計算子代理。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchYL_integrate [--procs 3] | --check | --page

═══ 讀法（寫死於 2026-10-03 23:40（台北），在算任何本件數字之前；⚠ 本線看過：營量 v1／營飆 v1 正式 T1、早年加上櫃重跑（營量 v1 早年 2005-02～2014-12
    上市＋上櫃 +21.8%／−34.4%、營量趨勢 +14.0%／−36.7%）、資金比例合併 blend 的表；⛔ 沒看過任何「單一規則」36 格的輸出）═══
 I1 固定部分（登錄 §一）：進場訊號 ＝ 營量 v1／營飆 v1 同一組 AND 訊號（T1 版）；訊號日次一交易日開盤進、等權、一檔一格、續抱中再出訊號不加碼（引擎本來就擋）；
    出場 ＝ 第 H 個交易日收盤（research11.fixed_exit：進場根算第 1 根；壞根界線 next_bad[k−20]；T1 資料尾補回 ＝ rerun17.t1_censor 同式）；成本 0.585%／來回；停止交易強制出場開
    主世界 ＝ researchT1fix.build_ctx(True)（edc6f 快照、AND T1）；H90 的出場欄本檔照同一式算，閘：重算的 H60、H120（xpos、g）＝ AND 表逐列相同
    早年世界 ＝ 上市＋上櫃版面（~/earlydata/eotc_f65bb03e11，researchEarlyOTC_rerun.make_world("O", "W_B")：AND T1＋R8 減資截斷，事件 ＝ 上市官方＋上市偵測＋上櫃官方＋上櫃偵測）；
      H90 同式＋R8 截斷（researchYLretest.exits_H 同式）；閘：重算 H60、H120 ＝ 早年 AND_mtm 逐列相同
      ⚠ 引用必附（裁定 seq283）：上櫃 2007-07～12 除權息未還原；上櫃減資 2007～2012 為偵測、非官方；2005-01～2007-06 只有上市
 I2 格（登錄 §二）：H ∈ {60, 90, 120} × S ∈ {10, 15, 20} × G ∈ {無, 0050>200MA} × P ∈ {relvol, 抽籤} ＝ 36 格
    G 有閘 ＝ 進場日 e 的前一日（訊號日）0050 還原收盤 ＞ 200 日均（rerun17.regime_mask，同營飆 v1 的 t−1 閘；早年用早年版面 0050）⇒ 訊號表先篩
    P relvol ＝ 營量 v1 的引擎參數：simulate_mtm(..., default_rng(7000＋r), log=[], d_max=None, pick="relvol", queue_days=0)；relvol 只排序、⇒ 跑 r＝0（另驗 r＝1 權益逐位元相同）
    P 抽籤 ＝ 營飆 v1 的引擎參數：simulate_mtm(..., default_rng(1000＋r))，r ＝ 0～199，報 200 顆中位
    閘：H60·S20·無·relvol ＝ resultsT1fix c13 t1 r0；H120·S10·閘·抽籤 ＝ c1 t1 r0～199（eq_sha、年化、回落 repr）
 I3 段（登錄 §三）：主窗 2017-03-02～2026-08-24 一條權益，探索 2017-03-02～2021-12-30、確認 2022-01-03～2026-08-24 切段讀（rerun17.win_metrics）；
    早年 2005-02-01～2014-12-31（登錄寫 2005-01；AND 訊號 2005-02-01 起建 ⇒ 窗首取訊號起點，照記）
    退化（挑前排除）：探索段平均持股 ＜ S÷2（audit 逐日）或現金 ＞ 50%（1 − 持股市值 ÷ 權益 的段內平均）
    挑格：探索段 先合格、再比 年化÷|回落|（中位；同分年化高）；判定：確認、早年各對 0050 同段，取較嚴（使用者判準：合格＝年化 ＞ 0050 且 比值 ≥ 0050；另列＝只贏年化）
    挑中格 ＝ 營量 v1 或營飆 v1 ⇒ 結論寫「合成沒有帶出新格」；確認段不是全新（看過營量／營飆在該段的表現）⇒ 結論最多「暫定」
 I4 取代判法（裁定 seq282 §三 ＝ seq265）：對 67:33 合併臂（營飆 2/3：營量 1/3，每日再平衡 ＝ researchYL_blend ①）同顆種子配對：
    d_t ＝ r_挑中格,t − r_67:33,t（營飆 r 配挑中格 r；營量只有一條）；200 顆平均 ⇒ 月分群 CR0（researchYLtrend.cr0_mean 同式）⇒ 平均 × 245 的 95% CI
    「取代」＝ 確認段 CI 下緣 ＞ 0 且 早年段平均差 ＞ 0；否則 ⇒ 只進前瞻紀錄並列；另報探索段、對營量 v1、營飆 v1 同法的 CI（描述）
    早年 67:33 ＝ 早年世界的 H60·S20·無·relvol（＝營量 v1 規則）與 H120·S10·閘·抽籤（＝營飆 v1 規則）同法合併
 I5 對照（登錄 §四）：營量 v1、營飆 v1、67:33、0050 同段；同訊號隨機 1,000 次 ＝ 挑中格的每一筆窗內訊號（G 篩前）換成「同一訊號日、當天與次日都有有效 K 棒的隨機股」
    （母體 ＝ 該世界 load_universe ∩ gate3；同日抽不重複；relvol ＝ 當根成交額 ÷ 前 60 根中位數（researchp1 同式）；出場 ＝ 同 H 的 fixed_exit＋T1；早年不做 R8），
    G 照挑中格的閘、引擎 ＝ 挑中格同參數、種子 i；抽樣 default_rng([20261003, 世界, i])；p ＝ 假比值 ≥ 挑中格比值中位 的比例（探索、確認、早年各報）
 I6 必報（挑中格）：各年報酬（200 顆中位）、MDD 發生期（每顆峰／谷日 ⇒ 谷日最常見的月與占比、r0 的峰谷）、平均持股、現金比例、換手（每年買進金額 ÷ 平均權益）與成本（換手 × 0.585%）；
    與營量 v1、營飆 v1 的持股重疊（按金額，researchYL_blend.holdings_w 同式；營飆同顆）；現實版（researchSlip 現實版、＋C5 低消 20 元；A ＝ 25 萬 ÷ S）主窗
    早年月營收逐年覆蓋率（上市、上櫃分列）：該年每個「有有效 K 棒的股-月」中有當月營收的比例（母體 ＝ 早年世界 load_universe ∩ gate3）；本規則不用法人 ⇒「上櫃 2014-12 前法人不可判定」不影響，照記
 I7 描述（不計 N；登錄 §四）：挑中格實際交易（全部顆數合併、去重）⇒ 進場時「從起漲點累計處置次數」（起漲點 ＝ researchYL_flowexit.anchor_before；處置起日落在 [t, e−1]，
    meta/disposal.csv 普通股；dispcum C2 同口徑）0／1／2／3+ 分組：筆數、持有期間從進場後最高收盤回落 ≥ 20%／30% 的比例、平均報酬 ⇒ 只當風險提示，⛔ 不進規則
    早年處置資料 2010-12 起 ⇒ 早年只算進場 ≥ 2011-01 的筆，照記
 I8 IFRS 敏感度（裁定 seq282 §一；描述、不計 N）：早年上市＋上櫃版（W_B 2005-02～2014-12、W_A 2012-06～2014-12），營量 v1 與營量趨勢（乙_T3_H40）
    訊號用到的營收期別 p ＝ 訊號日當下最新一列營收面板（signal_pos ≤ 訊號位置，同 research13.and_flags）；「回看 24 個月跨到 2013-01」＝ p−24 ＜ 2013-01 ≤ p ⇒ p ∈ [2013-01, 2014-12] ⇒ 剔除
    剔除後重算 200 顆（引擎、價格、閘照 researchEarlyOTC_rerun），報年化、回落、標籤是否改變；閘：不剔除時 ＝ resultsEarlyOTC/seeds.csv.gz 同版同窗同格（repr）
 I9 查核（--check）：① 閘 G 逐日迴圈重算（0050 200 日均）抽 50 列；② H90 出場逐根迴圈重算抽 30 列（主、早年各 15）；③ 挑格與判定依 cells 表逐格重算；
    ④ 67:33 合併與配對差、CR0 CI 逐日迴圈重算（確認段）；⑤ IFRS 剔除逐列重找期別抽 30 列 ⇒ 0 不同才算過；並附主程式閘
輸出 backtest/resultsYL_integrate/
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import sys
import time
from multiprocessing import Pool

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import data as D
from backtest import research11 as R
from backtest import rerun17 as RR

TIME = "2026-10-03 23:40（台北）"
OUT = "backtest/resultsYL_integrate"
HS, SS, GS, PS = (60, 90, 120), (10, 15, 20), (False, True), ("relvol", "抽籤")
NSEED = 200
NFAKE = 1000
if os.environ.get("IG_QUICK"):                                # 煙霧測試（不是交件）：少量種子、另一個輸出夾
    NSEED, NFAKE, OUT = 3, 3, "/tmp/ig_quick"
SEG_M = {"探索": ("2017-03-02", "2021-12-30"), "確認": ("2022-01-03", "2026-08-24")}
MSHA = "f65bb03e114a5e10336d661218c63e6e68b08b85"
NOTE3 = "上櫃 2007-07～12 除權息未還原；上櫃減資 2007～2012 為偵測、非官方；2005-01～2007-06 只有上市"
_W: dict = {}


def ck(H, S, G, P):
    return f"H{H}·S{S}·{'閘' if G else '無'}·{P}"


CELLS = [(H, S, G, P) for H in HS for S in SS for G in GS for P in PS]
KEY = {ck(*c): c for c in CELLS}
YL, YF = ck(60, 20, False, "relvol"), ck(120, 10, True, "抽籤")


def label(c, m, b):
    if not (np.isfinite(c) and np.isfinite(m)) or m == 0:
        return "—"
    return "合格" if (c > b["cagr"] and c / abs(m) >= b["cagr"] / abs(b["mdd"])) else ("另列" if c > b["cagr"] else "不合格")


ORDER = {"不合格": 0, "另列": 1, "合格": 2, "—": -1}


def sha(eq):
    return hashlib.sha256(np.asarray(eq, float).tobytes()).hexdigest()[:16]


# ═════════════ 出場欄 ═════════════
def exits_for(T, Hs, cal, uni, EVD=None, ncal0=None):
    """AND 表 ⇒ {H: (xpos, g)}（fixed_exit＋T1＋可選 R8；同 researchYLtrend.feat／researchYLretest.exits_H）。"""
    ncal0 = len(cal) if ncal0 is None else ncal0
    out = {H: (np.full(len(T), -1, np.int64), np.full(len(T), np.nan)) for H in Hs}
    cache = {}
    sid = T["sid"].to_numpy(); kk = T["k"].to_numpy(int)
    for i, (s_, k) in enumerate(zip(sid, kk)):
        if s_ not in cache:
            cache[s_] = R.load_bars(s_, uni.get(s_, "twse"), cal)
        B = cache[s_]
        if B is None:
            continue
        idx, o, c, nbar = B["idx"], B["o"], B["c"], B["next_bad"]; n = len(idx)
        nb = nbar[max(0, k - 20)]
        for H in Hs:
            r = R.fixed_exit(o, c, k, H, nb)
            if r:
                out[H][0][i] = int(idx[r[0]]); out[H][1][i] = r[1]
            elif D.exit_pos(k + 1, H) >= n and nb > n - 1 and int(idx[n - 1]) == ncal0 - 1:
                out[H][0][i] = ncal0; out[H][1][i] = float(c[n - 1] / o[k + 1] - 1.0)
    if EVD:
        ent = T["entry_pos"].to_numpy(int); pc = {}
        for s_, lst in EVD.items():
            ii = np.flatnonzero(sid == s_)
            if not len(ii):
                continue
            if s_ not in pc:
                st = D.load_stock(s_, "twse", cal); pc[s_] = (st.df["open"].to_numpy(float), st.df["close"].to_numpy(float))
            of_, cf_ = pc[s_]
            for pe, pL in lst:
                for i in ii:
                    for H in Hs:
                        xp, gg = out[H]
                        if xp[i] < 0 or not (ent[i] <= pL and xp[i] >= pe):
                            continue
                        xp[i] = pL; gg[i] = cf_[pL] / of_[ent[i]] - 1.0
    return out


# ═════════════ 世界 ═════════════
def main_world(log):
    from backtest import researchT1fix as T1
    ctx = T1.build_ctx(True)
    cal = ctx["cal"]; n0 = len(cal); w0, w1 = ctx["w0"], ctx["w1"]
    AND = ctx["AND"].copy()
    ex = exits_for(AND, HS, cal, ctx["mk"])
    gate = {}
    for H in (60, 120):
        gate[f"主 H{H} xpos 不同"] = int((ex[H][0] != AND[f"xpos_H{H}"].to_numpy(np.int64)).sum())
        gate[f"主 H{H} g 差＞1e−12"] = int(np.nansum(np.abs(ex[H][1] - AND[f"g_H{H}"].to_numpy(float)) > 1e-12))
    AND["xpos_H90"], AND["g_H90"] = ex[90]
    e = AND["entry_pos"].to_numpy()
    base = AND[(e >= w0) & (e <= w1)].copy()
    reg = RR._G["regime"]
    SF = R.stop_force_days(R.valid_from_data(sorted(ctx["closes"]), ctx["mk"], cal), w1)
    bench = RR._G["bench"]
    segp = {"主窗": (w0, w1), **{sg: (int(cal.searchsorted(pd.Timestamp(a))), int(cal.searchsorted(pd.Timestamp(b)))) for sg, (a, b) in SEG_M.items()}}
    b50 = {sg: RR.bench_row(cal, bench, x, y + 1) for sg, (x, y) in segp.items()}
    W = {"name": "主", "cal": cal, "w0": w0, "w1": w1, "closes": ctx["closes"], "opens": ctx["opens"], "NP": ctx["ncal"], "SF": SF, "segp": segp, "b50": b50,
         "base": base, "reg": reg, "uni": ctx["mk"], "data": D.DATA, "AND": AND, "ctx": ctx}
    W["SIG"] = {G: (base[reg[base["entry_pos"].to_numpy() - 1]] if G else base) for G in GS}
    log(f"[主世界] 窗內訊號 {len(base)}｜有閘 {len(W['SIG'][True])}｜閘 {gate}")
    return W, gate


def early_world(log, procs):
    from backtest import researchEarlyOTC_rerun as EO
    W0 = EO.make_world("O", "W_B", MSHA, procs, log)
    cal = W0["cal"]; T = W0["AND_full"].copy(); uni = D.load_universe().set_index("stock_id")["market"]
    EV = EO.events("O", "W_B", MSHA)
    posd = {d.strftime("%Y-%m-%d"): j for j, d in enumerate(cal)}
    EVD = {}
    for s_, e_, L_ in zip(EV["stock_id"], EV["e"], EV["L"]):
        if e_ in posd and L_ in posd:
            EVD.setdefault(s_, []).append((posd[e_], posd[L_]))
    ex = exits_for(T, HS, cal, uni, EVD)
    gate = {}
    for H in (60, 120):
        gate[f"早年 H{H} xpos 不同"] = int((ex[H][0] != T[f"xpos_H{H}"].to_numpy(np.int64)).sum())
        gate[f"早年 H{H} g 差＞1e−12"] = int(np.nansum(np.abs(ex[H][1] - T[f"g_H{H}"].to_numpy(float)) > 1e-12))
    T["xpos_H90"], T["g_H90"] = ex[90]
    w0, w1 = W0["w0"], W0["w1"]
    e = T["entry_pos"].to_numpy()
    base = T[(e >= w0) & (e <= w1)].copy()
    bench = RR.load_bench(cal); reg = RR.regime_mask(bench)
    W = {"name": "早年", "cal": cal, "w0": w0, "w1": w1, "closes": W0["closes"], "opens": W0["opens"], "NP": W0["ncal"], "SF": W0["SF"],
         "segp": {"早年": (w0, w1)}, "b50": {"早年": W0["b50"]["全窗"]}, "base": base, "reg": reg, "uni": uni, "data": D.DATA, "AND": T, "W0": W0}
    W["SIG"] = {G: (base[reg[base["entry_pos"].to_numpy() - 1]] if G else base) for G in GS}
    # 價格補齊（AND_full 的股都在 W0 closes 裡）
    miss = sorted(set(base["sid"]) - set(W["closes"]))
    if miss:
        raise SystemExit(f"⛔ 早年價格缺 {miss[:5]}")
    log(f"[早年世界] 窗內訊號 {len(base)}｜有閘 {len(W['SIG'][True])}｜閘 {gate}")
    return W, gate


# ═════════════ 引擎 ═════════════
def eng(W, key, r, sig=None, audit=True):
    H, S, G, P = KEY[key]
    sig = W["SIG"][G] if sig is None else sig
    au = [] if audit else None
    if P == "relvol":
        o = R.simulate_mtm(sig, f"H{H}", S, np.random.default_rng(RR.P1_SEED0 + r), W["closes"], W["opens"], W["NP"], return_equity=True,
                           log=[], d_max=None, pick="relvol", queue_days=0, stop_force=W["SF"], audit=au)
    else:
        o = R.simulate_mtm(sig, f"H{H}", S, np.random.default_rng(RR.P10_SEED0 + r), W["closes"], W["opens"], W["NP"], return_equity=True,
                           stop_force=W["SF"], audit=au)
    return o, au


def stats(W, o, au, S):
    eq = np.asarray(o["equity"], float); hv = np.asarray(o["hold_val"], float)
    cnt = np.zeros(len(eq) + 1)
    for a in au:
        cnt[a["t"]] += 1 if a["side"] == "buy" else -1
    hold = np.cumsum(cnt)[:len(eq)]
    row = {}
    for sg, (x, y) in W["segp"].items():
        c_, m_, _ = RR.win_metrics(eq, o["first"], o["end"], x, y)
        row[f"{sg}_年化"] = float(c_); row[f"{sg}_回落"] = float(m_)
        row[f"{sg}_持股"] = float(np.mean(hold[x:y + 1])); row[f"{sg}_現金"] = float(1.0 - np.mean(hv[x:y + 1] / eq[x:y + 1]))
        bs = [a for a in au if a["side"] == "buy" and x <= a["t"] <= y]
        yrs = (y - x + 1) / 245.0
        row[f"{sg}_買進每年"] = len(bs) / yrs
        row[f"{sg}_換手每年"] = float(sum(a["amt"] for a in bs) / np.mean(eq[x:y + 1]) / yrs)
    return row, eq


def job(args):
    wn, key, r = args
    W = _W[wn]
    o, au = eng(W, key, r)
    row, eq = stats(W, o, au, KEY[key][1])
    row.update({"世界": wn, "格": key, "r": r, "eq_sha": sha(eq), "first": int(o["first"]), "end": int(o["end"]), "trades": int(o["trades"])})
    return row


def job_eq(args):
    wn, key, r = args
    W = _W[wn]
    o, au = eng(W, key, r)
    keep = key == _W.get("PK") or r < 50
    return key, r, np.asarray(o["equity"], float), int(o["first"]), int(o["end"]), (au if keep else None)


# ═════════════ 假訊號（同訊號隨機）═════════════
def bars_job(args):
    sid, mk = args
    B = R.load_bars(sid, mk, _W["bcal"])
    if B is None:
        return sid, None
    return sid, (B["idx"], B["o"], B["c"], B["amt"], B["next_bad"])


def fake_job(args):
    wn, key, i = args
    W = _W[wn]; H, S, G, P = KEY[key]
    rng = np.random.default_rng([20261003, 0 if wn == "主" else 1, i])
    BY = W["BYDAY"]; BB = W["BARS"]; ncal0 = len(W["cal"])
    rows = []
    for d, cnt_ in W["DAYCNT"]:
        pool = BY.get(d)
        if pool is None or not len(pool):
            continue
        pick = rng.choice(len(pool), size=min(cnt_, len(pool)), replace=False)
        for j in pick:
            sid, k = pool[j]
            idx, o, c, amt, nbar = BB[sid]; n = len(idx)
            nb = nbar[max(0, k - 20)]
            rel = np.nan
            if k >= 60:
                med = float(np.nanmedian(amt[k - 60:k]))
                rel = float(amt[k]) / med if med > 0 and np.isfinite(amt[k]) else np.nan
            r_ = R.fixed_exit(o, c, k, H, nb)
            if r_:
                xp, g = int(idx[r_[0]]), float(r_[1])
            elif D.exit_pos(k + 1, H) >= n and nb > n - 1 and int(idx[n - 1]) == ncal0 - 1:
                xp, g = ncal0, float(c[n - 1] / o[k + 1] - 1.0)
            else:
                xp, g = -1, np.nan
            rows.append((sid, k, int(idx[k]), int(idx[k + 1]), xp, g, rel))
    F = pd.DataFrame(rows, columns=["sid", "k", "pos", "entry_pos", f"xpos_H{H}", f"g_H{H}", "relvol"])
    if G:
        F = F[W["reg"][F["entry_pos"].to_numpy() - 1]]
    F["relvol"] = F["relvol"].fillna(0.0)
    o, au = eng({**W, "closes": W["FCL"], "opens": W["FOP"], "SF": W["SF_F"]}, key, i, sig=F, audit=False)
    eq = np.asarray(o["equity"], float); row = {"世界": wn, "i": i, "列": int(len(F))}
    for sg, (x, y) in W["segp"].items():
        c_, m_, _ = RR.win_metrics(eq, o["first"], o["end"], x, y)
        row[f"{sg}_年化"] = float(c_); row[f"{sg}_回落"] = float(m_)
    return row


def prep_fake(W, key, procs, log):
    from backtest import universe_gate as UG
    D.DATA = W["data"]
    stocks = pd.read_csv(os.path.join(D.DATA, "meta", "stocks.csv"), dtype=str)
    uni = D.load_universe().merge(UG.gate3(stocks)[["stock_id"]], on="stock_id")
    _W["bcal"] = W["cal"]
    with Pool(procs) as pool:
        BB = {s: v for s, v in pool.map(bars_job, list(zip(uni["stock_id"], uni["market"])), chunksize=8) if v is not None}
    BY = {}
    for s, (idx, o, c, amt, nb) in BB.items():
        ok = np.flatnonzero(np.isfinite(o[1:]) & (o[1:] > 0)) if len(idx) > 1 else []
        for k in ok:
            if k >= 249:
                BY.setdefault(int(idx[k]), []).append((s, int(k)))
    for d in BY:
        BY[d].sort()
    base = W["base"]
    dc = base.groupby("pos").size()
    W["BARS"] = BB; W["BYDAY"] = BY; W["DAYCNT"] = list(zip(dc.index.astype(int), dc.to_numpy(int)))
    sids = sorted(BB)
    cl, op = RR.load_prices(sids, W["cal"], uni.set_index("stock_id")["market"], "branch")
    padn = W["NP"] - len(W["cal"])
    if padn:
        cl = {s: np.r_[v, v[-1:]].astype(v.dtype) for s, v in cl.items()}; op = {s: np.r_[v, np.float32(np.nan)].astype(v.dtype) for s, v in op.items()}
    W["FCL"], W["FOP"] = cl, op
    W["SF_F"] = R.stop_force_days(R.valid_from_data(sids, uni.set_index("stock_id")["market"], W["cal"]), W["w1"])
    log(f"[假訊號準備 {W['name']}] 母體 {len(BB)} 檔｜訊號日 {len(dc)}")


# ═════════════ 配對差 ═════════════
def cr0(d, months):
    m = float(d.mean()); u = d - m
    s = pd.Series(u).groupby(months).sum().to_numpy()
    return m, float(np.sqrt((s ** 2).sum()) / len(d))


def blend_eq(eF, fF, nF, eY, fY, nY, w=2 / 3):
    first = min(fF, fY); end = min(nF, nY)
    n = len(eF); rF = np.zeros(n); rY = np.zeros(n)
    rF[1:end] = eF[1:end] / eF[:end - 1] - 1; rY[1:end] = eY[1:end] / eY[:end - 1] - 1
    return np.cumprod(1 + w * rF + (1 - w) * rY), first, end


def paired(EQ_a, EQ_b, W, seeds):
    """⇒ {段: (年化差, lo, hi, 月數)}；EQ_x[r] ＝ 權益。"""
    out = {}
    for sg, (x, y) in W["segp"].items():
        acc = None
        for r in seeds:
            a = EQ_a[r]; b = EQ_b[r]
            d = (a[x + 1:y + 1] / a[x:y] - 1.0) - (b[x + 1:y + 1] / b[x:y] - 1.0)
            acc = d if acc is None else acc + d
        acc = acc / len(seeds)
        months = np.array([str(dd)[:7] for dd in W["cal"][x + 1:y + 1]])
        m, se = cr0(acc, months)
        out[sg] = (m * 245, (m - 1.96 * se) * 245, (m + 1.96 * se) * 245, int(len(set(months))))
    return out


# ═════════════ 主程式 ═════════════
def run(a, log):
    T0 = time.time(); os.makedirs(OUT, exist_ok=True)
    S = {"讀法寫死": TIME, "登錄": "營收趨勢整合 seq1 sha 71cd40fb9ac104e1（裁定 seq282 §三）", "早年標註": NOTE3}
    Wm, gm = main_world(log)
    We, ge = early_world(log, a.procs)
    S["閘"] = {**gm, **ge}
    _W["主"], _W["早年"] = Wm, We
    # ── 36 格 ──
    jobs = []
    for wn in ("主", "早年"):
        for key, (H, S_, G, P) in KEY.items():
            for r in (range(2) if P == "relvol" else range(NSEED)):
                jobs.append((wn, key, r))
    sp = os.path.join(OUT, "seeds.csv.gz")
    if os.environ.get("IG_RESUME") and os.path.exists(sp):           # 續跑：同一支程式、同一份輸入算出來的 36 格逐種子檔（第一次跑被背景時限砍在假訊號段）
        SE = pd.read_csv(sp, float_precision="round_trip", dtype={"eq_sha": str}); log(f"[續跑] 讀 {sp}（{len(SE)} 列）")
    else:
        with Pool(a.procs) as pool:
            ROWS = pool.map(job, jobs, chunksize=4)
        SE = pd.DataFrame(ROWS); SE.to_csv(sp, index=False, float_format="%.17g")
    log(f"[36 格] {len(SE)} 次｜{time.time() - T0:.0f}s")
    rv = SE[SE["格"].map(lambda k: KEY[k][3] == "relvol")]
    S["閘"]["relvol 格 r1 ＝ r0（權益 sha 不同格數）"] = int(sum(g["eq_sha"].nunique() != 1 for _, g in rv.groupby(["世界", "格"])))
    ref = pd.read_csv("backtest/resultsT1fix/seeds.csv.gz", dtype={"eq_sha": str}, float_precision="round_trip")
    m13 = SE[(SE["世界"] == "主") & (SE["格"] == YL) & (SE["r"] == 0)].iloc[0]; r13 = ref[(ref["key"] == "c13") & (ref["var"] == "t1") & (ref["r"] == 0)].iloc[0]
    S["閘"]["營量 v1 格 ＝ T1fix c13 r0（eq_sha、年化、回落）"] = bool(m13["eq_sha"] == r13["eq_sha"] and repr(float(m13["主窗_年化"])) == repr(float(r13["cagr"]))
                                                      and repr(float(m13["主窗_回落"])) == repr(float(r13["mdd"])))
    m1 = SE[(SE["世界"] == "主") & (SE["格"] == YF)].sort_values("r").reset_index(drop=True)
    r1 = ref[(ref["key"] == "c1") & (ref["var"] == "t1")].sort_values("r").reset_index(drop=True)
    S["閘"]["營飆 v1 格 ＝ T1fix c1 r0～199（不同顆數）"] = int(sum(m1.loc[i, "eq_sha"] != r1.loc[i, "eq_sha"] or repr(float(m1.loc[i, "主窗_年化"])) != repr(float(r1.loc[i, "cagr"]))
                                                         or repr(float(m1.loc[i, "主窗_回落"])) != repr(float(r1.loc[i, "mdd"])) for i in range(min(len(m1), len(r1)))))
    log(f"[閘] {S['閘']}")
    # ── 彙總、退化、挑格 ──
    C = []
    for (wn, key), g in SE[(SE["r"] < NSEED)].groupby(["世界", "格"]):
        H, S_, G, P = KEY[key]
        g = g[g["r"] == 0] if P == "relvol" else g
        W = _W[wn]
        row = {"世界": wn, "格": key, "H": H, "S": S_, "閘": "有" if G else "無", "優先": P, "顆數": len(g)}
        for sg in W["segp"]:
            c_, m_ = float(g[f"{sg}_年化"].median()), float(g[f"{sg}_回落"].median())
            row.update({f"{sg}_年化": c_, f"{sg}_回落": m_, f"{sg}_比值": c_ / abs(m_) if m_ else np.nan, f"{sg}_標籤": label(c_, m_, W["b50"][sg]),
                        f"{sg}_年化p10": float(g[f"{sg}_年化"].quantile(.1)), f"{sg}_年化p90": float(g[f"{sg}_年化"].quantile(.9)),
                        f"{sg}_持股": float(g[f"{sg}_持股"].median()), f"{sg}_現金": float(g[f"{sg}_現金"].median()),
                        f"{sg}_買進每年": float(g[f"{sg}_買進每年"].median()), f"{sg}_換手每年": float(g[f"{sg}_換手每年"].median())})
        C.append(row)
    C = pd.DataFrame(C)
    CM = C[C["世界"] == "主"].copy()
    CM["退化"] = (CM["探索_持股"] < CM["S"] / 2) | (CM["探索_現金"] > 0.5)
    el = CM[~CM["退化"]].copy()
    el["_q"] = el["探索_標籤"].map(ORDER)
    el = el.sort_values(["_q", "探索_比值", "探索_年化"], ascending=[False, False, False])
    PK = el.iloc[0]["格"]
    CE = C[C["世界"] == "早年"].set_index("格")
    C = C.merge(CM[["格", "退化"]], on="格", how="left")
    C.to_csv(os.path.join(OUT, "cells.csv"), index=False, float_format="%.8g")
    pr = CM.set_index("格").loc[PK]
    lab_c, lab_e = pr["確認_標籤"], CE.loc[PK, "早年_標籤"]
    final = min((lab_c, lab_e), key=lambda x: ORDER[x])
    S["挑格"] = {"挑中": PK, "探索": [float(pr["探索_年化"]), float(pr["探索_回落"]), pr["探索_標籤"]], "確認": [float(pr["確認_年化"]), float(pr["確認_回落"]), lab_c],
                "早年": [float(CE.loc[PK, "早年_年化"]), float(CE.loc[PK, "早年_回落"]), lab_e], "件標籤（兩段取嚴）": final,
                "退化排除格": CM[CM["退化"]]["格"].tolist(), "探索段合格格數": int((CM["探索_標籤"] == "合格").sum()),
                "合成沒有帶出新格": PK in (YL, YF), "排序前 5": el["格"].head(5).tolist()}
    S["0050"] = {wn: _W[wn]["b50"] for wn in _W}
    log(f"[挑格] {S['挑格']}")
    # ── 挑中格、營量、營飆 權益（兩世界）⇒ 67:33 配對 ──
    P_pk = KEY[PK][3]
    EQ = {}
    need = []
    for wn in ("主", "早年"):
        for key in {PK, YL, YF}:
            seeds = [0] if KEY[key][3] == "relvol" else list(range(NSEED))
            need += [(wn, key, r) for r in seeds]
    AUD = {}
    _W["PK"] = PK
    for wn in ("主", "早年"):
        EQ[wn] = {}; AUD[wn] = {}
        with Pool(a.procs) as pool:
            res = pool.map(job_eq, [x for x in need if x[0] == wn], chunksize=4)
        for key, r, eq, f_, e_, au in res:
            EQ[wn].setdefault(key, {})[r] = (eq, f_, e_); AUD[wn].setdefault(key, {})[r] = au
    seeds = list(range(NSEED))
    CMP = {}
    for wn in ("主", "早年"):
        W = _W[wn]
        get = lambda key, r: EQ[wn][key][r if KEY[key][3] == "抽籤" else 0]
        A_ = {r: get(PK, r)[0] for r in seeds}
        B67 = {}
        for r in seeds:
            eF, fF, nF = get(YF, r); eY, fY, nY = get(YL, r)
            B67[r] = blend_eq(eF, fF, nF, eY, fY, nY)[0]
        CMP[wn] = {"對67:33": paired(A_, B67, W, seeds), "對營量v1": paired(A_, {r: get(YL, r)[0] for r in seeds}, W, seeds),
                   "對營飆v1": paired(A_, {r: get(YF, r)[0] for r in seeds}, W, seeds)}
        # 67:33 本身的年化／回落（中位）
        rows67 = []
        for r in seeds:
            eF, fF, nF = get(YF, r); eY, fY, nY = get(YL, r)
            eqb, fb, nb = blend_eq(eF, fF, nF, eY, fY, nY)
            rows67.append({sg: RR.win_metrics(eqb, fb, nb, x, y)[:2] for sg, (x, y) in W["segp"].items()})
        CMP[wn]["67:33 本身"] = {sg: [float(np.median([z[sg][0] for z in rows67])), float(np.median([z[sg][1] for z in rows67])),
                                    label(float(np.median([z[sg][0] for z in rows67])), float(np.median([z[sg][1] for z in rows67])), W["b50"][sg])] for sg in W["segp"]}
        if wn == "主":
            np.savez_compressed(os.path.join(OUT, "pair_main.npz"), pk=np.array([A_[r] for r in seeds]), b67=np.array([B67[r] for r in seeds]))
    cc = CMP["主"]["對67:33"]["確認"]; ee = CMP["早年"]["對67:33"]["早年"]
    S["對67:33"] = {"確認": cc, "早年": ee, "探索": CMP["主"]["對67:33"]["探索"],
                   "判": ("取代（確認段 CI 下緣 ＞ 0 且早年平均差 ＞ 0）" if (cc[1] > 0 and ee[0] > 0) else "不取代 ⇒ 只進前瞻紀錄並列")}
    S["對照"] = {wn: {k: {sg: list(v_) for sg, v_ in v.items()} if k != "67:33 本身" else v for k, v in CMP[wn].items()} for wn in CMP}
    log(f"[67:33] {S['對67:33']}")
    # ── 必報：各年、MDD 期、重疊、處置描述 ──
    S["必報"] = must_report(PK, EQ, AUD, log)
    # ── 現實版 ──
    S["現實版"] = slip_real(PK, a, log)
    # ── 假訊號 ──
    FK = []
    for wn in ("主", "早年"):
        prep_fake(_W[wn], PK, a.procs, log)
        with Pool(a.procs) as pool:
            FK += pool.map(fake_job, [(wn, PK, i) for i in range(NFAKE)], chunksize=8)
        for k_ in ("BARS", "BYDAY", "FCL", "FOP"):
            _W[wn].pop(k_, None)
    FK = pd.DataFrame(FK); FK.to_csv(os.path.join(OUT, "fake.csv.gz"), index=False, float_format="%.8g")
    fk = {}
    for wn in ("主", "早年"):
        W = _W[wn]; g = FK[FK["世界"] == wn]
        for sg in W["segp"]:
            if sg == "主窗":
                continue
            rp = CM.set_index("格").loc[PK, f"{sg}_比值"] if wn == "主" else CE.loc[PK, "早年_比值"]
            ratio = g[f"{sg}_年化"] / g[f"{sg}_回落"].abs()
            fk[sg] = {"假比值中位": float(ratio.median()), "假年化中位": float(g[f"{sg}_年化"].median()), "挑中格比值": float(rp), "p": float((ratio >= rp).mean())}
    S["同訊號隨機"] = fk
    log(f"[假訊號] {fk}")
    # ── 早年營收覆蓋 ──
    S["早年月營收覆蓋"] = rev_coverage(log)
    # ── IFRS ──
    S["IFRS"] = ifrs(a, log)
    S["耗時秒"] = round(time.time() - T0)
    json.dump(S, open(os.path.join(OUT, "summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    log(f"[完] {S['耗時秒']}s")
    g = S["閘"]
    bad = any(v for k, v in g.items() if isinstance(v, (int, np.integer)) and not isinstance(v, bool)) or not g["營量 v1 格 ＝ T1fix c13 r0（eq_sha、年化、回落）"]
    if bad:
        raise SystemExit(f"⛔ 閘不過 {g}")


def must_report(PK, EQ, AUD, log):
    from backtest import researchYL_blend as BL
    from backtest import researchYL_flowexit as FE
    out = {}
    for wn in ("主", "早年"):
        W = _W[wn]; cal = W["cal"]; w0, w1 = W["w0"], W["w1"]
        seeds = sorted(EQ[wn][PK])
        yrs = sorted(set(cal[w0:w1 + 1].year))
        ends = [int(np.flatnonzero((cal.year == y) & (np.arange(len(cal)) <= w1))[-1]) for y in yrs]
        YR = []
        PT = []
        for r in seeds:
            eq = EQ[wn][PK][r][0]; prev = w0; yr = {}
            for y, b in zip(yrs, ends):
                yr[str(y)] = float(eq[b] / eq[prev] - 1); prev = b
            YR.append(yr)
            seg = eq[w0:w1 + 1]; pk_ = np.maximum.accumulate(seg); dd = seg / pk_ - 1; tr = int(np.argmin(dd)); pkk = int(np.argmax(seg[:tr + 1]))
            PT.append((str(cal[w0 + pkk].date()), str(cal[w0 + tr].date())))
        trm = pd.Series([t[1][:7] for t in PT]).value_counts()
        out[wn] = {"各年報酬（中位）": {y: float(np.median([z[y] for z in YR])) for y in YR[0]},
                   "MDD 谷底最常見月": [trm.index[0], float(trm.iloc[0] / len(PT))], "r0 峰谷": PT[0]}
        # 重疊（按金額）
        sids = sorted(set(W["closes"]))
        SI = {s: i for i, s in enumerate(sids)}
        ov = {"營量v1": [], "營飆v1": []}
        for r in seeds[:50]:
            eA, _, _ = EQ[wn][PK][r]; n = len(eA)
            WA, _ = BL.holdings_w(AUD[wn][PK][r], eA, W["closes"], n, SI)
            for nm, key in (("營量v1", YL), ("營飆v1", YF)):
                rr = r if KEY[key][3] == "抽籤" else 0
                eB = EQ[wn][key][rr][0]
                WB, _ = BL.holdings_w(AUD[wn][key][rr], eB, W["closes"], n, SI)
                ov[nm].append(float(np.mean(np.minimum(WA, WB).sum(axis=0)[w0:w1 + 1])))
        out[wn]["持股重疊（按金額，前 50 顆中位）"] = {k: float(np.median(v)) for k, v in ov.items()}
        # 處置累計描述
        D.DATA = W["data"]
        dsp = pd.read_csv(os.path.join(D.DATA, "meta", "disposal.csv"), dtype=str)
        dsp = dsp[dsp.get("sec_kind", pd.Series(["普通股"] * len(dsp))) == "普通股"] if "sec_kind" in dsp else dsp
        stp = {}
        for s_, d_ in zip(dsp["stock_id"], dsp["start_date"]):
            stp.setdefault(s_, []).append(int(cal.searchsorted(pd.Timestamp(d_))))
        H = KEY[PK][0]
        tr_ = {}
        for r in seeds:
            for a_ in AUD[wn][PK][r]:
                if a_["side"] == "buy" and w0 <= a_["t"] <= w1:
                    tr_[(a_["sid"], int(a_["t"]))] = 1
        rows = []
        sig = W["base"].set_index(["sid", "entry_pos"])
        for (s_, e_) in tr_:
            if wn == "早年" and cal[e_] < pd.Timestamp("2011-01-01"):
                continue
            c = np.asarray(W["closes"][s_], float)[:len(cal)]
            t, _ = FE.anchor_before(c, e_)
            nd = sum(1 for p in stp.get(s_, []) if t <= p <= e_ - 1)
            try:
                rr_ = sig.loc[(s_, e_)]
                rr_ = rr_.iloc[0] if isinstance(rr_, pd.DataFrame) else rr_
                xp, g = int(rr_[f"xpos_H{H}"]), float(rr_[f"g_H{H}"])
            except KeyError:
                continue
            if xp < 0:
                continue
            hi = np.nanmax(c[e_:min(xp, len(c) - 1) + 1]); lo_after = np.nanmin(c[e_ + int(np.nanargmax(c[e_:min(xp, len(c) - 1) + 1])):min(xp, len(c) - 1) + 1])
            rows.append({"累計處置": min(nd, 3), "回落20": lo_after <= hi * 0.8, "回落30": lo_after <= hi * 0.7, "報酬": g - R.COST})
        DG = pd.DataFrame(rows)
        out[wn]["處置累計描述"] = {("3+" if k == 3 else str(k)): {"筆": int(len(v)), "回落≥20%": float(v["回落20"].mean()), "回落≥30%": float(v["回落30"].mean()),
                                                              "平均報酬": float(v["報酬"].mean())} for k, v in DG.groupby("累計處置")} if len(DG) else {}
        log(f"[必報 {wn}] {json.dumps(out[wn], ensure_ascii=False, default=str)[:600]}")
    return out


def slip_real(PK, a, log):
    from backtest import researchSlip as SL
    from backtest import researchT1fix as T1
    from backtest import tradability as TR
    W = _W["主"]; RR.use_snapshot(); D.DATA = W["data"]
    H, S_, G, P = KEY[PK]
    SL.CELLS["PK"] = {"名": PK, "rule": f"H{H}", "N": S_, "seed0": RR.P1_SEED0 if P == "relvol" else RR.P10_SEED0, "A": 250_000 / S_}
    sig = W["SIG"][G]
    T1._G.update(cal=W["cal"], NPX=len(W["cal"]) + 1)
    with Pool(a.procs) as pool:
        X = dict(pool.map(T1._load_x, [(s, W["uni"].get(s, "twse")) for s in sorted(set(sig["sid"]))], chunksize=8))
    trad_full = {s: {"trd": v["trd"][:len(W["cal"])]} for s, v in X.items() if v is not None}
    try:
        off = TR.load_official()
    except Exception:
        off = {}
    dl = TR.delist_status(trad_full, W["cal"], official=off)
    SL._G.clear(); SL._G.update(dict(cal=W["cal"], NP=W["NP"], closes=W["closes"], opens=W["opens"], w0=W["w0"], w1=W["w1"], SF=W["SF"], dl=dl, X=X, ncal=len(W["cal"])))
    spec = dict(SL.ARMS); out = {}
    for arm in ("現實版（C1 0.3%＋C2 50 萬＋C3＋C4）", "現實版＋C5 低消 20 元"):
        sg_, op, cost, kw = SL.arm_inputs("PK", spec[arm], sig, X, W["closes"], W["opens"])
        rows = []
        for r in ([0] if P == "relvol" else range(NSEED)):
            R.COST = cost
            try:
                if P == "relvol":
                    o = R.simulate_mtm(sg_, f"H{H}", S_, np.random.default_rng(RR.P1_SEED0 + r), W["closes"], op, W["NP"], log=[], d_max=None, pick="relvol",
                                       queue_days=0, return_equity=True, **kw)
                else:
                    o = R.simulate_mtm(sg_, f"H{H}", S_, np.random.default_rng(RR.P10_SEED0 + r), W["closes"], op, W["NP"], return_equity=True, **kw)
            finally:
                R.COST = SL.BASE_COST
            eq = np.asarray(o["equity"], float)
            rows.append({sg: RR.win_metrics(eq, o["first"], o["end"], x, y)[:2] for sg, (x, y) in W["segp"].items()})
        out[arm] = {sg: [float(np.median([z[sg][0] for z in rows])), float(np.median([z[sg][1] for z in rows])),
                         label(float(np.median([z[sg][0] for z in rows])), float(np.median([z[sg][1] for z in rows])), W["b50"][sg])] for sg in W["segp"]}
    log(f"[現實版] {out}")
    return out


def rev_coverage(log):
    from backtest import universe_gate as UG
    W = _W["早年"]; D.DATA = W["data"]
    stocks = pd.read_csv(os.path.join(D.DATA, "meta", "stocks.csv"), dtype=str)
    uni = D.load_universe().merge(UG.gate3(stocks)[["stock_id"]], on="stock_id")
    per = json.load(open(os.path.expanduser(f"~/earlydata/eotc_{MSHA[:10]}/otc/otc_periods.json")))
    rev = {}
    import glob
    for f in sorted(glob.glob(os.path.join(D.DATA, "mops", "revenue_hist", "*.csv"))):
        x = pd.read_csv(f, dtype=str, usecols=["stock_id", "period", "當月營收"])
        v = pd.to_numeric(x["當月營收"], errors="coerce")
        for s_, p_, ok in zip(x["stock_id"], x["period"], v.notna()):
            if ok:
                rev[(s_, p_)] = True
    cnt = {}
    for s_ in uni["stock_id"]:
        d = pd.read_csv(os.path.join(D.DATA, "stocks", f"{s_}.csv"), dtype=str, usecols=["date", "close"])
        d = d[pd.to_numeric(d["close"], errors="coerce") > 0]
        mons = sorted(set(d["date"].str[:7]))
        for m in mons:
            if not ("2005-01" <= m <= "2014-12"):
                continue
            mk = "上櫃" if any(lo[:7] <= m <= hi[:7] for lo, hi in per.get(s_, [])) else "上市"
            k = (mk, m[:4]); c_ = cnt.setdefault(k, [0, 0]); c_[0] += 1; c_[1] += int((s_, m) in rev)
    out = {f"{mk}|{y}": [v[1] / v[0], v[0]] for (mk, y), v in sorted(cnt.items())}
    log(f"[營收覆蓋] {out}")
    return out


def ifrs(a, log):
    from backtest import researchEarlyOTC_rerun as EO
    ref = pd.read_csv("backtest/resultsEarlyOTC/seeds.csv.gz", float_precision="round_trip")
    pan = pd.read_csv(os.path.expanduser(f"~/earlydata/eotc_{MSHA[:10]}/sig_otc/panel_rev.csv.gz"), dtype={"stock_id": str}, usecols=["stock_id", "period", "signal_pos"])
    pan = pan.sort_values(["stock_id", "signal_pos"])
    PP = {s: (g["signal_pos"].to_numpy(int), g["period"].to_numpy()) for s, g in pan.groupby("stock_id")}

    def per_of(s, pos):
        if s not in PP:
            return None
        sp, pr = PP[s]; j = int(np.searchsorted(sp, pos, side="right")) - 1
        return pr[j] if j >= 0 else None
    out = {}; drops = []
    for win in ("W_B", "W_A"):
        W = EO.make_world("O", win, MSHA, a.procs, log)
        EO._W[f"IF|{win}"] = W
        for cell, (sig, H) in list(W["SIG"].items()):
            pp = [per_of(s, int(p)) for s, p in zip(sig["sid"], sig["pos"])]
            cross = np.array([p is not None and "2013-01" <= p <= "2014-12" for p in pp])
            drops += [{"窗": win, "格": cell, "sid": s, "pos": int(p), "期別": q, "剔除": bool(x)} for s, p, q, x in zip(sig["sid"], sig["pos"], pp, cross)]
            W["SIG"][f"{cell}|剔"] = (sig[~cross], H)
            out[f"{win}|{cell}"] = {"訊號": int(len(sig)), "剔除": int(cross.sum())}
        with Pool(a.procs) as pool:
            rows = pool.map(EO.run_one, [(f"IF|{win}", c, r) for c in list(W["SIG"]) for r in range(NSEED)], chunksize=4)
        R_ = pd.DataFrame(rows)
        for cell in ("營量v1", "乙_T3_H40"):
            full = R_[R_["格"] == cell].sort_values("r").reset_index(drop=True); cut = R_[R_["格"] == f"{cell}|剔"].sort_values("r").reset_index(drop=True)
            rf = ref[(ref["版"] == "O") & (ref["窗"] == win) & (ref["格"] == cell)].sort_values("r").reset_index(drop=True)
            g_ = int(sum(repr(float(full.loc[i, "全窗_年化"])) != repr(float(rf.loc[i, "全窗_年化"])) for i in range(min(len(full), len(rf)))))
            b = W["b50"]["全窗"]
            c0, m0 = float(full["全窗_年化"].median()), float(full["全窗_回落"].median()); c1, m1 = float(cut["全窗_年化"].median()), float(cut["全窗_回落"].median())
            out[f"{win}|{cell}"].update({"閘：不剔除 ＝ EarlyOTC（不同顆數）": g_, "原": [c0, m0, label(c0, m0, b)], "剔除後": [c1, m1, label(c1, m1, b)],
                                         "標籤改變": label(c0, m0, b) != label(c1, m1, b), "0050": [b["cagr"], b["mdd"]]})
            if win == "W_B":
                for sg in EO.SUBSEG:
                    bb = W["b50"][sg]
                    x0, y0 = float(full[f"{sg}_年化"].median()), float(full[f"{sg}_回落"].median()); x1, y1 = float(cut[f"{sg}_年化"].median()), float(cut[f"{sg}_回落"].median())
                    out[f"{win}|{cell}"][f"分段 {sg}"] = {"原": [x0, y0, label(x0, y0, bb)], "剔除後": [x1, y1, label(x1, y1, bb)]}
        EO._W.pop(f"IF|{win}", None)
    pd.DataFrame(drops).to_csv(os.path.join(OUT, "ifrs_rows.csv.gz"), index=False)
    log(f"[IFRS] {json.dumps(out, ensure_ascii=False)[:1500]}")
    return out


# ═════════════ 查核 ═════════════
def check(a, log):
    S = json.load(open(os.path.join(OUT, "summary.json"), encoding="utf-8")); C = pd.read_csv(os.path.join(OUT, "cells.csv"))
    errs = []; info = {}
    # ① 閘 G 逐日（主世界）
    from backtest import researchT1fix as T1
    ctx = T1.build_ctx(True); cal = ctx["cal"]; bench = RR._G["bench"]
    AND = ctx["AND"]; rng = np.random.default_rng(20261003)
    nd = 0
    for i in rng.choice(len(AND), 50, replace=False):
        e = int(AND["entry_pos"].iloc[i]); t = e - 1
        ma = np.mean(bench[t - 199:t + 1]) if t >= 199 else np.nan
        mine = bool(np.isfinite(ma) and bench[t] > ma)
        if mine != bool(RR._G["regime"][t]):
            nd += 1; errs.append(f"閘 {AND['sid'].iloc[i]} {e}")
    info["① 閘逐日"] = nd
    # ② H90 逐根（主 15）
    nd = 0; Hs = [90]
    for i in rng.choice(len(AND), 15, replace=False):
        s_, k = AND["sid"].iloc[i], int(AND["k"].iloc[i])
        st = D.load_stock(s_, ctx["mk"].get(s_, "twse"), cal)
        tr = np.flatnonzero(st.df["traded"].to_numpy())
        B = R.load_bars(s_, ctx["mk"].get(s_, "twse"), cal)
        nb = B["next_bad"][max(0, k - 20)]
        xb = (k + 1) + 90 - 1                              # 進場根 k＋1 算第 1 根 ⇒ 第 90 根
        mine = (int(tr[xb]), float(st.df["close"].to_numpy()[tr[xb]] / st.df["open"].to_numpy()[tr[k + 1]] - 1)) if (xb < len(tr) and xb < nb) else None
        ex = exits_for(AND.iloc[[i]], Hs, cal, ctx["mk"])[90]
        if mine is not None and (mine[0] != int(ex[0][0]) or abs(mine[1] - float(ex[1][0])) > 1e-9):
            nd += 1; errs.append(f"H90 {s_} {k} {mine} {ex[0][0]} {ex[1][0]}")
    info["② H90 逐根（主 15 列）"] = nd
    # ③ 挑格重算
    cm = C[C["世界"] == "主"].copy()
    b = S["0050"]["主"]["探索"]
    best = None
    for _, r in cm.iterrows():
        deg = r["探索_持股"] < r["S"] / 2 or r["探索_現金"] > 0.5
        if deg:
            continue
        lab = label(r["探索_年化"], r["探索_回落"], b)
        key = (ORDER[lab], r["探索_比值"], r["探索_年化"])
        if best is None or key > best[0]:
            best = (key, r["格"])
    info["③ 挑格重算"] = best[1]
    if best[1] != S["挑格"]["挑中"]:
        errs.append(f"挑格 {best[1]} / {S['挑格']['挑中']}")
    # ④ 67:33 配對 CI 逐日（確認段）
    Z = np.load(os.path.join(OUT, "pair_main.npz")); pk, b67 = Z["pk"], Z["b67"]
    w0 = int(cal.searchsorted(pd.Timestamp(SEG_M["確認"][0]))); w1 = int(cal.searchsorted(pd.Timestamp(SEG_M["確認"][1])))
    dsum = np.zeros(w1 - w0)
    for r in range(pk.shape[0]):
        for t in range(w0 + 1, w1 + 1):
            dsum[t - w0 - 1] += (pk[r, t] / pk[r, t - 1] - 1) - (b67[r, t] / b67[r, t - 1] - 1)
    d = dsum / pk.shape[0]
    mo = [str(x)[:7] for x in cal[w0 + 1:w1 + 1]]
    m = d.mean(); grp = {}
    for v, mm in zip(d - m, mo):
        grp[mm] = grp.get(mm, 0.0) + v
    se = np.sqrt(sum(v * v for v in grp.values())) / len(d)
    mine = [m * 245, (m - 1.96 * se) * 245, (m + 1.96 * se) * 245]
    ref = S["對67:33"]["確認"]
    if any(abs(x - y) > 1e-9 for x, y in zip(mine, ref[:3])):
        errs.append(f"CI {mine} / {ref}")
    info["④ 確認段 67:33 CI 迴圈"] = mine
    # ⑤ IFRS 期別逐列
    IR = pd.read_csv(os.path.join(OUT, "ifrs_rows.csv.gz"), dtype={"sid": str})
    pan = pd.read_csv(os.path.expanduser(f"~/earlydata/eotc_{MSHA[:10]}/sig_otc/panel_rev.csv.gz"), dtype={"stock_id": str}, usecols=["stock_id", "period", "signal_pos"])
    nd = 0
    for r in IR.sample(30, random_state=20261003).itertuples():
        g = pan[(pan["stock_id"] == r.sid) & (pan["signal_pos"] <= r.pos)]
        p = g.loc[g["signal_pos"].idxmax(), "period"] if len(g) else None
        x = p is not None and "2013-01" <= p <= "2014-12"
        if (p if p is not None else "nan") != (r.期別 if isinstance(r.期別, str) else "nan") or x != bool(r.剔除):
            nd += 1; errs.append(f"IFRS {r.sid} {r.pos} {p}/{r.期別}")
    info["⑤ IFRS 期別"] = nd
    out = {"讀法寫死": TIME, "比對": info, "不同的筆": errs[:20], "主程式閘": S["閘"], "通過": not errs}
    json.dump(out, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    log(f"[查核] {info}｜{errs[:5]}")


# ═════════════ 網頁 ═════════════
def page(log):
    S = json.load(open(os.path.join(OUT, "summary.json"), encoding="utf-8")); C = pd.read_csv(os.path.join(OUT, "cells.csv"))
    CKp = os.path.join(OUT, "check.json"); CK = json.load(open(CKp, encoding="utf-8")) if os.path.exists(CKp) else None
    CSS = open("backtest/list_yl13_hist.py", encoding="utf-8").read().split('CSS = """')[1].split('"""')[0]
    CSS += ("\ntd.l,th.l{text-align:left;white-space:normal}small{color:#666}.warn{border-left:4px solid #d64045;padding:6px 10px;background:#fff4f4}"
            ".ok{border-left:4px solid #2b6cb0;padding:8px 12px;background:#eef4fb}.big{font-size:1.05rem}li{margin:.35em 0}tr.pk td{background:#fff7d6}")
    P1 = lambda v: "—" if v is None or not np.isfinite(v) else f"{v * 100:+.1f}%"
    P_ = lambda v: "—" if v is None or not np.isfinite(v) else f"{v * 100:.0f}%"
    PT = lambda v: "—" if v is None or not np.isfinite(v) else f"{v * 100:+.1f} 點"
    e = html.escape
    pk = S["挑格"]; PK = pk["挑中"]; cmp = S["對67:33"]
    H = ['<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">',
         "<title>營收趨勢整合</title>", f"<style>{CSS}</style></head><body><main>",
         "<h1>營收趨勢整合：營量、營飆合成一條規則（36 格挑 1）</h1>",
         f"<p class='warn'>⚠ 確認段不是全新的資料（營量、營飆在這段的表現已經看過），結論最多「暫定」。早年段用上市＋上櫃版面：{e(NOTE3)}。</p>"]
    concl = (f"<b>先講結論</b>：探索段挑中 <b>{e(PK)}</b>"
             + ("（＝ 現行的營量 v1 或營飆 v1 ⇒ 合成沒有帶出新格）" if pk["合成沒有帶出新格"] else "") + "；"
             f"確認段 {P1(pk['確認'][0])}／{P1(pk['確認'][1])}（{pk['確認'][2]}）、早年段 {P1(pk['早年'][0])}／{P1(pk['早年'][1])}（{pk['早年'][2]}）⇒ 兩段取嚴：<b>{pk['件標籤（兩段取嚴）']}</b>。"
             f"<br>對現行 67:33 合併：確認段年化差 {PT(cmp['確認'][0])}（95% CI {PT(cmp['確認'][1])}～{PT(cmp['確認'][2])}），早年段 {PT(cmp['早年'][0])} ⇒ <b>{e(cmp['判'])}</b>。")
    H.append(f"<div class='ok big'>{concl}</div>")
    H.append(f"<p class='lead'>讀法寫死 {e(S['讀法寫死'])}。進場訊號、等權、固定天數出場都照正式；只動四個參數：抱幾天 H、幾格 S、大盤閘、候選多時誰先。"
             f"抽籤的格報 200 顆種子中位。探索段先合格、再比年化÷回落挑一格。"
             + (f"查核：{'通過' if CK['通過'] else '有不同'}。" if CK else "") + "</p>")
    b = S["0050"]
    H.append("<h2>一、36 格（主窗：探索／確認；早年）</h2><div class='wrap'><table><tr><th class='l'>格</th><th>探索</th><th>確認</th><th>早年</th><th>探索持股／現金</th></tr>")
    cm = C[C["世界"] == "主"].set_index("格"); ce = C[C["世界"] == "早年"].set_index("格")
    for key in cm.sort_values(["探索_比值"], ascending=False).index:
        r, q = cm.loc[key], ce.loc[key]
        cls = " class='pk'" if key == PK else ""
        tag = ("（營量 v1）" if key == YL else ("（營飆 v1）" if key == YF else "")) + ("　退化" if r["退化"] else "")
        H.append(f"<tr{cls}><td class='l'>{e(key)}{tag}</td><td>{P1(r['探索_年化'])}／{P1(r['探索_回落'])}<br><small>{r['探索_標籤']}</small></td>"
                 f"<td>{P1(r['確認_年化'])}／{P1(r['確認_回落'])}<br><small>{r['確認_標籤']}</small></td><td>{P1(q['早年_年化'])}／{P1(q['早年_回落'])}<br><small>{q['早年_標籤']}</small></td>"
                 f"<td>{r['探索_持股']:.1f}／{P_(r['探索_現金'])}</td></tr>")
    H.append(f"</table></div><p class='note'>0050：探索 {P1(b['主']['探索']['cagr'])}／{P1(b['主']['探索']['mdd'])}、確認 {P1(b['主']['確認']['cagr'])}／{P1(b['主']['確認']['mdd'])}、"
             f"早年 {P1(b['早年']['早年']['cagr'])}／{P1(b['早年']['早年']['mdd'])}。排序依探索段比值；黃底 ＝ 挑中格。</p>")
    # 對照
    H.append("<h2>二、對照（年化差 ＝ 挑中格 − 對照，同顆配對、月分群 95% CI）</h2><div class='wrap'><table><tr><th class='l'>對照</th><th>探索</th><th>確認</th><th>早年</th></tr>")
    OC = S["對照"]
    for k in ("對67:33", "對營量v1", "對營飆v1"):
        cells_ = [OC["主"][k]["探索"], OC["主"][k]["確認"], OC["早年"][k]["早年"]]
        H.append(f"<tr><td class='l'>{k}</td>" + "".join(f"<td>{PT(v[0])}<br><small>{PT(v[1])}～{PT(v[2])}</small></td>" for v in cells_) + "</tr>")
    s67 = {**OC["主"]["67:33 本身"], **OC["早年"]["67:33 本身"]}
    H.append(f"</table></div><p class='note'>67:33 本身：探索 {P1(s67['探索'][0])}／{P1(s67['探索'][1])}（{s67['探索'][2]}）、確認 {P1(s67['確認'][0])}／{P1(s67['確認'][1])}（{s67['確認'][2]}）、"
             f"早年 {P1(s67['早年'][0])}／{P1(s67['早年'][1])}（{s67['早年'][2]}）。</p>")
    fk = S["同訊號隨機"]
    H.append("<p class='note'>同訊號隨機（每個訊號日換成當天隨機股，1,000 次）：" + "；".join(f"{sg} 假比值中位 {v['假比值中位']:.2f}、挑中格 {v['挑中格比值']:.2f}、p ＝ {v['p']:.3f}" for sg, v in fk.items()) + "。</p>")
    # 必報
    mr = S["必報"]
    H.append("<h2>三、挑中格必報</h2><ul class='note'>")
    for wn, v in mr.items():
        H.append(f"<li>{wn}：各年報酬 " + "、".join(f"{y} {P1(x)}" for y, x in v["各年報酬（中位）"].items()) +
                 f"；最大回落谷底最常見在 {v['MDD 谷底最常見月'][0]}（{P_(v['MDD 谷底最常見月'][1])} 的種子）；"
                 f"與營量 v1 持股重疊 {P_(v['持股重疊（按金額，前 50 顆中位）']['營量v1'])}、與營飆 v1 {P_(v['持股重疊（按金額，前 50 顆中位）']['營飆v1'])}。</li>")
    pr = cm.loc[PK]
    H.append(f"<li>主窗平均持股 {pr['主窗_持股']:.1f} 檔、現金 {P_(pr['主窗_現金'])}、每年買進 {pr['主窗_買進每年']:.0f} 筆、換手 {pr['主窗_換手每年']:.1f} 倍／年（成本約 {pr['主窗_換手每年'] * 0.585:.1f}%／年）。</li>")
    for arm, v in S["現實版"].items():
        H.append(f"<li>{e(arm)}：確認段 {P1(v['確認'][0])}／{P1(v['確認'][1])}（{v['確認'][2]}）、探索 {P1(v['探索'][0])}（{v['探索'][2]}）。</li>")
    H.append("</ul>")
    H.append("<h3>持有中累計處置次數（只當風險提示，不進規則）</h3><div class='wrap'><table><tr><th class='l'>世界</th><th>累計處置</th><th>筆</th><th>回落≥20%</th><th>回落≥30%</th><th>平均報酬</th></tr>")
    for wn, v in mr.items():
        for k, x in v["處置累計描述"].items():
            H.append(f"<tr><td class='l'>{wn}</td><td>{k}</td><td>{x['筆']}</td><td>{P_(x['回落≥20%'])}</td><td>{P_(x['回落≥30%'])}</td><td>{P1(x['平均報酬'])}</td></tr>")
    H.append("</table></div><p class='note'>累計處置 ＝ 起漲點到進場前一天的處置次數；回落 ＝ 持有期間從進場後最高收盤跌多少。早年只算 2011 起進場（處置資料 2010-12 起）。</p>")
    cov = S["早年月營收覆蓋"]
    H.append("<h3>早年月營收覆蓋率</h3><p class='note'>" + "；".join(f"{k.replace('|', ' ')} {P_(v[0])}" for k, v in cov.items()) + "。本規則不用法人資料。</p>")
    # IFRS
    H.append("<h2>四、早年 IFRS 換軌敏感度（描述）</h2><p class='note'>剔除「營收 24 月新高的回看期跨到 2013-01」的訊號（用到的營收期別在 2013-01～2014-12）後重算。</p>"
             "<div class='wrap'><table><tr><th class='l'>窗｜策略</th><th>剔除筆／訊號</th><th>原</th><th>剔除後</th><th>0050</th><th>標籤改變</th></tr>")
    for k, v in S["IFRS"].items():
        if "原" not in v:
            continue
        H.append(f"<tr><td class='l'>{e(k.replace('W_B', '2005-02～2014-12').replace('W_A', '2012-06～2014-12'))}</td><td>{v['剔除']}／{v['訊號']}</td>"
                 f"<td>{P1(v['原'][0])}／{P1(v['原'][1])}<br><small>{v['原'][2]}</small></td><td>{P1(v['剔除後'][0])}／{P1(v['剔除後'][1])}<br><small>{v['剔除後'][2]}</small></td>"
                 f"<td>{P1(v['0050'][0])}／{P1(v['0050'][1])}</td><td>{'是' if v['標籤改變'] else '否'}</td></tr>")
    H.append("</table></div>")
    H.append("</main></body></html>")
    open(os.path.join(OUT, "營收趨勢整合.html"), "w", encoding="utf-8").write("\n".join(H))
    log("[網頁] 完成")


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--procs", type=int, default=3)
    ap.add_argument("--check", action="store_true"); ap.add_argument("--page", action="store_true"); a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True); T0 = time.time()
    logf = open(os.path.join(OUT, "run_check.log" if a.check else ("run_page.log" if a.page else "run.log")), "a", encoding="utf-8")

    def log(m):
        m = f"[{time.time() - T0:6.0f}s] {m}"; print(m, flush=True); logf.write(str(m) + "\n"); logf.flush()
    if a.check:
        check(a, log)
    elif a.page:
        page(log)
    else:
        run(a, log)
        page(log)


if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
"""PREREG高成長加速 seq1（台股策略線登錄 sha 494ddaced4b5d4a7，2026-10-11 00:09；裁定 seq329 §三發號、N_組合 ＋1（E1／E2 兩格挑 1）；
事後重切 ⇒ 最多暫定；裁定 seq328 §二必附句）——回測線計算子代理。⛔ 只計算：不 commit、不改既有程式與結果夾；用語「假訊號」；⛔ 不給買賣建議。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchRevAccel run [--procs 2] [--reps 200] [--fake 200] [--smoke]
    ...                                                      -m backtest.researchRevAccel page          # 網頁 backtest/resultsRevAccel/高成長加速.html
    抽樣查核（獨立寫法）：... -m backtest.researchRevAccel_check

⭐ 讀法寫死時間：見 TIME（台北）；寫死前 ⛔ 沒算任何本件數字（只看過登錄全文 seq1、裁定 seq328／seq329、情報 #33 全文（事件層數字本來就看過 ⇒ 登錄已標事後重切）、
   既有程式（researchRevLimitUp、researchPRE5core、researchYLmargin、researchT1fix）與資料格式）。

═══ 讀法（A 標；登錄沒寫清楚、執行者補的都在這裡）═══
 A1 sha：登錄全文去掉含「pw1 line」那一行後 sha256 前 16 碼核對才跑（信箱只讀）：seq1 ＝ 494ddaced4b5d4a7（裁定 seq329 發號那一版；00:35 起已搬到
    _封存-台股策略線附件-舊seq/）、seq2 ＝ d0f01caf695247e3（台股 00:35：只加末段「裁定 seq329 §三（寫死）」、判定一字未動；本檔寫死前已 diff 核過）⇒ 兩封都核
 A2 版面（＝ researchRevLimitUp M2 同一組，直接用它的 World 與快取 ~/rluwork/world_*.pkl）：主段 ＝ rerun17 快照 H2D（edc6f8002f；日曆 2015-01-05～2026-09-24）；
    早年 ＝ ~/earlydata/eotc_f65bb03e11/otc/data（上市＋上櫃；日曆 2004-02-11～2014-12-31；⚠ 上櫃日 K 2007-07 起）；股票 ＝ UG.gate3（GATE_V2 開）∩ 四碼、
    首碼 1～9、非 91xx；⭐ 含已下市；價格 ＝ D.load_stock（還原），收盤 ffill；月營收、產業 ＝ tw-stock-data origin/main（執行時 sha）git archive（唯讀）
 A3 母體（決策日 d ＝ t0 的前一個交易日，用 d 收盤以前的資料）：d 有 K 棒 ∧ UG.pit_valid(d) ∧ amt20(d) ≥ 5,000 萬（含 d 的最近 20 根有效 K 棒原始成交金額平均；
    不足 20 根 ⇒ 不在母體）∧ 產業不是「金融保險」「生技醫療業」（industry_pit pit 版，月初判、月內沿用＝ researchRevLimitUp.fb_matrix；早年合併類「化學生技醫療」
    分不開 ⇒ 不剔，筆數照報）∧ 當月營收 ＞ 0
    ⚠ 5,000 萬是事件層 #33 原定義（裁定 seq328 §二：母體照事件層原定義）；營量 v1／營飆 v1 正式流動性閘是「20 日均量 ≥ 500 張」⇒ 兩者不同，照實寫（另報本件訊號中
      決策日 20 日均量 ≥ 500 張的占比）
    R1 排名版（描述）：d 當天「四碼 ∧ 有 K 棒 ∧ pit_valid ∧ 非金融生技」依 amt20 由大到小前 X%；X ＝ 2016-01-04 上述 5,000 萬母體檔數 ÷ 同日全市場檔數（researchRevLimitUp.r1_x）
 A4 年增（百分比）Y_M ＝ (當月營收 ÷ 去年當月營收 − 1) × 100；兩者都 ＞ 0 才有值，否則「沒值」；月營收同 (代號, 期別) 重複 ⇒ 取最後一列（PRE.load_rev）；
    上月年增 ＝ 期別 M−1 那一列同式（M−1 沒列 ⇒ 沒值）。⚠ 月營收是回抓版本（最後一列），不是第一次公布的值（同情報 #33 限制）
 A5 加速（期別 M）：當月營收 ＞ 0 ∧ Y_M ≥ 30 ∧ Y_{M−1} ≥ 30 ∧ Y_M − Y_{M−1} ≥ 20（比較都留 1e−9 浮點容差：≥ x − 1e−9）
 A6 t0(M) ＝ research34.rebalance_dates（M ≤ 2025-12：M＋1 月 10 日之後第一個交易日；M ≥ 2026-01：15 日之後；嚴格大於）⇒ 進場 e ＝ t0 開盤；
    d ＝ t0 − 1（日曆位置）；e 沒有有效開盤 ⇒ 不進（筆數照報）；同一檔已持有 ⇒ 不重買（引擎 held）
 A7 出場（seq308 §四：條件出場、⛔ 不設最長天數）：
    E1：e 之後每個 t0(M′)（M′ ＞ M、t0(M′) ＞ e）依序檢查該股期別 M′：Y_{M′} 沒值 ⇒ 賣（理由「年增沒值」；⭐ 補讀法，同好營收再加漲停 M7「不明、沒值都算」）；
        Y_{M′} ＜ 30 ⇒ 賣（「年增＜30%」）；Y_{M′} − Y_{M′−1} ≤ −20 ⇒ 賣（「轉減速」；Y_{M′−1} 沒值 ⇒ 這一條不成立）；兩條都成立 ⇒ 記「年增＜30%」
        ⇒ t0(M′) 起第一個可成交開盤賣；t0(M′) ≤ e 的期別不檢查（同 #26 M7）
    E2：e 起（含 e 收盤）持有期最高收盤 × 0.8 ≥ 當日收盤 ⇒ 次一交易日起第一個可成交開盤賣
    資料尾還沒出場 ⇒ 未完（墊檔日、以最後收盤計值、不賣；只影響窗外，窗尾持有照報）；停止交易 ⇒ 引擎 stop_force
 A8 引擎 research11.simulate_mtm（rule "F"）：10 槽、slot ＝ 前一日權益 ÷ 10、候選多於空位 ⇒ rng.permutation（default_rng(20261010＋r)）、⛔ 不遞補；
    停止交易強制出場：開；成本 0.585%／來回；200 顆種子報中位（＝ researchRevLimitUp.sim）
    現實版（researchSlip「現實版」逐字、N＝10，＝ researchRevLimitUp M8）：C1 每邊 ＋0.3%；C2 單邊衝擊 σ20 × √(5 萬 ÷ ADV20)；C3 一字漲停買不到、停牌買不到、
      一字跌停賣不掉；C4 進出價 ＝ (開＋高＋低＋收)÷4；C5 低消 20 元加 0（照報）；引擎 tradable＋delist；判定以 0.585% 版為準，現實版同表並報
 A9 段：主窗 2017-03-02～2026-08-24（rerun17 win 讀法）；探索 2017-03-02～2021-12-30（登錄「2017-03～2021-12」）；確認 2022-01-03～2026-08-24（「資料尾」讀成主窗尾
    2026-08-24 ＝ 0050 錨同窗）；出場判斷用到 2026-09-24
    早年 2005～2014（early 版面；照 researchRevLimitUp M9「既有月營收早年規則」：月營收覆蓋 PRE.coverage 上市各月 ≥ 90% 的年份才可判，判定窗從「其後各年都 ≥ 90%」
    的第一年起；IFRS（期別 2013 的年增是 IFRS 對舊制）只照報占比、不剔）
 A10 退化（裁定 seq325；登錄必報）：⭐ 先算持股與現金、先寫 degeneracy.json（附台北時間）再彙總任何報酬；平均持股 ＜ 3 或平均現金 ＞ 30%（段內逐日平均、種子中位）
     ⇒ 該格照登錄排除並列出；挑格只在探索段非退化格中挑（全退化 ⇒ 在全部格裡同規則挑、標「全退化」、沒有可判的格）
 A11 挑格（0.585% 版）：探索段非退化格中合格者取比值最大；沒有合格 ⇒ 取比值最大（照報它在探索段不合格）；平手 ⇒ 年化高、格序（E1、E2）
     判定（使用者判準，對 0050 同段）：合格 ＝ 年化中位 ＞ 0050 且 年化中位 ÷ |回落中位| ≥ 0050；另列 ＝ 只過年化；其餘不合格；
     挑中格在確認段與早年段（可判時）的標籤兩段取較嚴；事後重切 ⇒ 兩段都合格也最多「暫定」、只進前瞻紀錄
 A12 假訊號臂（挑中格；researchRevLimitUp.fake_rows 同一套）：每個進場日 e 的訊號數不變 ⇒ 改成 e−1 母體裡隨機同數量的股（e 要有有效開盤），持有天數從挑中格
     （已完成）的「進場 → 出場」日曆位置差等機率抽；抽樣 default_rng([20261011, r])；200 抽；p ＝ 假訊號年化 ≥ 挑中格年化中位 的比例
 A13 描述（⛔ 不判、不計 N；挑中格同進場、各 50 顆）：固定持有 {20, 60, 120} 根（第 H 根收盤出）；R1 排名版；0050 在 200 日線上才買（決策日 d：0050 還原收盤 ＞ 含 d 的
     200 日均線）⚠ 0050 濾網的角色：「擋長空頭、不是急跌保護」
 A14 必報：等效獨立檔數（r＝0，換股日持股 N、ρ ＝ 前 60 日收盤日報酬兩兩相關平均、N_eff ＝ N ÷ (1＋(N−1)ρ)）；最大產業占幾檔（industry_pit 單層）；現金比例；
     持有天數分佈；各出場原因次數；窗尾仍持有（檔數與已持有天數）；一年內先跌 15%（250 日內收盤先碰 ≤ 進場價 × 0.85，早於 ≥ × 1.15）；各年報酬；訊號年增中位
     持股重疊率（裁定 seq328 §二、登錄「相鄰四者」）：本件挑中格 r＝0 的逐日持股中、同日也在對方持股裡的比例（本件有持股的日子平均；另報反向）：
       營量 v1、營飆 v1 ＝ researchRevLimitUp.yl_ref（researchT1fix.build_ctx(True) 重跑 r＝0；閘 eq_sha ＝ resultsT1fix c1／c13 t1 r0）
       #26 好營收再加漲停 ＝ resultsRevLimitUp 挑中格，用 researchRevLimitUp 同一套函式重跑 r＝0（閘：eq sha ＝ resultsRevLimitUp/seeds.csv.gz 同臂 r0）
       #17＋#10 好營收股價已認同 ＝ ~/pre5work/RevPriceOK_run.pkl 的 iv0（閘：eq0 sha ＝ resultsRevPriceOK/seeds.csv.gz 挑中格 |b r0）
 A15 結果句必附（登錄 §三、裁定 seq328 §二）：「抽籤型、多數個股會跌（事件層個股中位 −1.48%）」；「多重檢定邊緣（t ≈ 2.8 ＜ 3.38）」；
     「做多那一腿對母體 +1.42%，扣一趟成本後約剩 0.8%；基準是 5,000 萬等權母體、不是 0050」
 A16 ⚠ 減資價格斷點（裁定 seq329 §五）：正式引擎 hard_break 是否擋到現金減資／彌補虧損減資日另案查核中；本件照現行引擎跑，結果註記「減資斷點待查」
輸出 backtest/resultsRevAccel/：degeneracy.json（先寫）、summary.json、grid.csv、seeds.csv.gz、signals.csv.gz、run.log、高成長加速.html；大檔 ~/racwork/
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import pickle
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import universe_gate as UG                    # noqa: E402
from backtest import rerun17 as RR                          # noqa: E402
from backtest import research34 as R34                      # noqa: E402
from backtest import researchIndRev_prereg as PRE           # noqa: E402
from backtest import researchRevLimitUp as RL               # noqa: E402

UG.set_gate_v2(True)

TIME = "2026-10-11 00:44（台北）"
REG_SHA = "494ddaced4b5d4a7"
REG_SHA2 = "d0f01caf695247e3"
HERE = os.path.expanduser("~/tw-p17/backtest")
OUT = os.path.join(HERE, "resultsRevAccel")
PAGE = os.path.join(OUT, "高成長加速.html")
WORK = os.path.expanduser("~/racwork")
SEGS = RL.SEGS
EARLY = RL.EARLY
CELLS = ["E1", "E2"]
YMIN, DACC, DDEC = 30.0, 20.0, -20.0
EPS = 1e-9
E2_DD = 0.20
VOL500 = 500_000          # 500 張（股）
_G: dict = {}


def reg_check(shas=None):
    import glob as _g
    out = []
    for sha in (shas or (REG_SHA, REG_SHA2)):
        fs = [f for f in _g.glob(os.path.join(RL.MAILBOX, "**", "*.md"), recursive=True) if f"sha{sha}" in os.path.basename(f)]
        if len(fs) != 1:
            raise SystemExit(f"⛔ 信箱找不到唯一一封登錄全文 sha{sha}：{fs}")
        b = open(fs[0], "rb").read()
        h = hashlib.sha256(b"\n".join(l for l in b.split(b"\n") if b"pw1 line" not in l)).hexdigest()[:16]
        if h != sha:
            raise SystemExit(f"⛔ 登錄 sha {h} ≠ {sha}")
        out.append(os.path.relpath(fs[0], RL.MAILBOX))
    return out


# ═════════════ 年增與旗標 ═════════════
def yoy_tables(log):
    """A4／A5 ⇒ Y（period × sid，百分比，沒值 NaN）、ACC（加速 bool）、XF（E1 出場碼：0 不賣、1 年增＜30%、2 轉減速、3 年增沒值）。"""
    if "Y" in _G:
        return _G
    G = RL.load_rev(log)
    rv = G["rev"].to_numpy(float); rl = G["rev_ly"].to_numpy(float)
    with np.errstate(invalid="ignore", divide="ignore"):
        Y = np.where((rv > 0) & (rl > 0), (rv / rl - 1.0) * 100.0, np.nan)
    Yp = np.vstack([np.full((1, Y.shape[1]), np.nan), Y[:-1]])
    with np.errstate(invalid="ignore"):
        ACC = (rv > 0) & (Y >= YMIN - EPS) & (Yp >= YMIN - EPS) & (Y - Yp >= DACC - EPS)
        lo = ~(Y >= YMIN - EPS); dec = (Y - Yp <= DDEC + EPS)
    XF = np.where(~np.isfinite(Y), 3, np.where(lo, 1, np.where(dec, 2, 0)))
    _G.update(Y=pd.DataFrame(Y, index=G["rev"].index, columns=G["rev"].columns), Yp=pd.DataFrame(Yp, index=G["rev"].index, columns=G["rev"].columns),
              ACC=pd.DataFrame(ACC, index=G["rev"].index, columns=G["rev"].columns), XF=pd.DataFrame(XF, index=G["rev"].index, columns=G["rev"].columns))
    log(f"[年增] 加速（股-期）{int(ACC.sum()):,}；期別 {G['rev'].index[0]}～{G['rev'].index[-1]}")
    return _G


def t0_map(W, periods):
    rd = {**R34.rebalance_dates([M for M in periods if M <= "2025-12"], W.cal, 10), **R34.rebalance_dates([M for M in periods if M >= "2026-01"], W.cal, 15)}
    return {M: e for M, (_, e) in rd.items()}


def build_signals(W, U, log):
    """A3～A6 ⇒ 訊號列（s、d、e、M、t0、Y、Yp）＋ 計數。"""
    T = yoy_tables(log)
    ACC, Y, Yp = T["ACC"], T["Y"], T["Yp"]
    periods = list(ACC.index); T0 = t0_map(W, periods)
    cols = {s: j for j, s in enumerate(ACC.columns)}
    hcol = np.array([cols.get(s, -1) for s in W.sids]); has = hcol >= 0
    AV, YV, YPV = ACC.to_numpy(bool), Y.to_numpy(float), Yp.to_numpy(float)
    rows = []; st = {"加速（股-期，本版面股票）": 0, "其中 d 在母體": 0}
    for k, M in enumerate(periods):
        t0 = T0.get(M)
        if t0 is None or t0 < 1:
            continue
        a = np.zeros(W.S, bool); a[has] = AV[k, hcol[has]]
        if not a.any():
            continue
        st["加速（股-期，本版面股票）"] += int(a.sum())
        m = a & U[:, t0 - 1]
        st["其中 d 在母體"] += int(m.sum())
        for i in np.flatnonzero(m):
            j = hcol[i]
            rows.append((int(i), t0 - 1, t0, M, t0, float(YV[k, j]), float(YPV[k, j])))
    F = pd.DataFrame(rows, columns=["s", "d", "e", "M", "t0", "Y", "Yp"]).sort_values(["e", "s"]).reset_index(drop=True)
    return F, st, T0


def exit_rows(W, F, T0, cell):
    """A7 ⇒ rows（s、e、xk、x、why、key）。"""
    XF = _G["XF"]; periods = list(XF.index); cols = {s: j for j, s in enumerate(XF.columns)}; XV = XF.to_numpy(int)
    pidx = {M: k for k, M in enumerate(periods)}
    t0s = sorted((t, M) for M, t in T0.items())
    WHY = {1: "年增＜30%", 2: "轉減速", 3: "年增沒值"}
    out = []
    for s, e, M in zip(F["s"], F["e"], F["M"]):
        s, e = int(s), int(e)
        x, why = -1, "未完"
        if cell == "E1":
            j = cols.get(W.sids[s], -1)
            for t, M2 in t0s:
                if M2 <= M or t <= e:
                    continue
                f = XV[pidx[M2], j] if j >= 0 else 3
                if f != 0:
                    x = t; why = WHY[int(f)]
                    break
        else:
            c = W.C[s, e:]; rm = np.maximum.accumulate(c)
            w = np.flatnonzero(c <= rm * (1 - E2_DD) + 1e-12)
            if len(w):
                x = e + int(w[0]) + 1; why = "回落20%"
                if x >= W.n:
                    x, why = -1, "未完"
        out.append((s, e, "open", x, why, np.nan))
    return pd.DataFrame(out, columns=["s", "e", "xk", "x", "why", "key"])


# ═════════════ 相鄰策略持股（A14）═════════════
def vol20_share(W, F):
    """本件訊號中決策日 20 日均量 ≥ 500 張的占比（A3 照實寫）。"""
    cnt = ok = 0
    for s, d in zip(F["s"], F["d"]):
        sid = W.sids[int(s)]
        if "VOL" not in _G:
            _G["VOL"] = {}
        if sid not in _G["VOL"]:
            p = os.path.join(W.data, "stocks", f"{sid}.csv")
            x = pd.read_csv(p, dtype={"date": str}, usecols=["date", "close", "volume"]).drop_duplicates("date")
            x.index = pd.to_datetime(x["date"]); v = pd.to_numeric(x["volume"], errors="coerce").reindex(W.cal).to_numpy(float)
            bar = W.BAR[int(s)]; idx = np.flatnonzero(bar); v20 = np.full(W.n, np.nan)
            v20[idx] = pd.Series(v[idx]).rolling(20, min_periods=20).mean().to_numpy()
            _G["VOL"][sid] = v20
        v = _G["VOL"][sid][int(d)]
        if np.isfinite(v):
            cnt += 1; ok += int(v >= VOL500)
    return {"有值筆": cnt, "≥ 500 張筆": ok, "占比": ok / cnt if cnt else np.nan}


def ref26(WM, w0, w1, log):
    """#26 好營收再加漲停挑中格 r＝0（researchRevLimitUp 同一套）＋ 閘。"""
    S = json.load(open(os.path.join(HERE, "resultsRevLimitUp", "summary.json"), encoding="utf-8"))
    ch = S["判定"]["挑中格"]
    U, _ = RL.universe(WM, log)
    SIG, _, T0 = RL.build_signals(WM, U, log)
    SIG = SIG[(SIG["e"] >= w0) & (SIG["e"] <= w1)].reset_index(drop=True)
    F = RL.finalize_rows(WM, RL.exit_rows(WM, SIG, T0, ch), False)
    o, au = RL.sim(WM, F, False, 0, w1)
    eq = np.asarray(o["equity"], float); sha = hashlib.sha256(eq.tobytes()).hexdigest()[:16]
    ref = pd.read_csv(os.path.join(HERE, "resultsRevLimitUp", "seeds.csv.gz"), dtype={"sha": str})
    q = ref[(ref["arm"] == f"{ch}|b") & (ref["r"] == 0)].iloc[0]
    gate = bool(str(q["sha"]) == sha)
    log(f"[#26 r0] 挑中格 {ch}｜閘 eq sha ＝ resultsRevLimitUp {gate}")
    return {"格": ch, "閘": gate, "iv": RL.holdings(au, WM.n + 1)}


def ref17(log):
    S = json.load(open(os.path.join(HERE, "resultsRevPriceOK", "summary.json"), encoding="utf-8"))
    ch = S["判定"]["挑中格"]
    P = pickle.load(open(os.path.expanduser("~/pre5work/RevPriceOK_run.pkl"), "rb"))
    sha = hashlib.sha256(np.asarray(P["eq0"]).tobytes()).hexdigest()[:16]
    ref = pd.read_csv(os.path.join(HERE, "resultsRevPriceOK", "seeds.csv.gz"), dtype={"sha": str})
    q = ref[(ref["arm"] == f"{ch}|b") & (ref["r"] == 0)].iloc[0]
    gate = bool(str(q["sha"]) == sha and P["chosen"] == ch)
    log(f"[#17 r0] 挑中格 {ch}｜閘 eq0 sha ＝ resultsRevPriceOK {gate}")
    return {"格": ch, "閘": gate, "iv": P["iv0"]}


# ═════════════ 主流程 ═════════════
def run(a):
    global OUT, WORK
    if a.smoke:
        OUT = os.path.join(WORK, "smoke")
    os.makedirs(OUT, exist_ok=True); os.makedirs(WORK, exist_ok=True)
    log = RL.log_to(os.path.join(OUT, "run.log"))
    log(f"===== researchRevAccel run {RL.now_tpe()}（台北）｜讀法寫死 {TIME}｜reps {a.reps} fake {a.fake} smoke {a.smoke} =====")
    regf = reg_check(); log(f"[sha] {REG_SHA} ✔ {regf}")
    t00 = time.time()
    yoy_tables(log)
    WM = RL.World("main", a.procs, log)
    seg = {k: WM.segpos(*v) for k, v in SEGS.items()}
    assert seg["主窗"] == (WM.pos("2017-03-02"), WM.pos("2026-08-24"))
    Z = {k: RR.bench_row(WM.cal, WM.bench, x, y + 1) for k, (x, y) in seg.items()}
    g0 = (repr(Z["主窗"]["cagr"]) == repr(RL.ANCHOR[0]), repr(Z["主窗"]["mdd"]) == repr(RL.ANCHOR[1]))
    log(f"[0050] 主窗錨逐位元 {g0}")
    if not all(g0):
        raise SystemExit("⛔ 0050 錨不對")
    w0, w1 = seg["主窗"]
    U, OLD = RL.universe(WM, log)
    if a.smoke:
        U = U & (np.arange(WM.S) % 7 == 0)[:, None]
    SIG, LST, T0 = build_signals(WM, U, log)
    SIGw = SIG[(SIG["e"] >= w0) & (SIG["e"] <= w1)].reset_index(drop=True)
    log(f"[訊號] 全部 {len(SIG)}、主窗內 {len(SIGw)}｜{json.dumps(LST, ensure_ascii=False)}")
    FB_, FR_ = {}, {}
    for c in CELLS:
        rw = exit_rows(WM, SIGw, T0, c)
        FB_[c] = RL.finalize_rows(WM, rw, False); FR_[c] = RL.finalize_rows(WM, rw, True)
        log(f"[出場] {c}：base 可進 {len(FB_[c])}（e 無有效開盤剔 {len(rw) - len(FB_[c])}）、未完 {int(FB_[c]['end'].sum())}｜{FB_[c]['why'].value_counts().to_dict()}")
    S_out = SIGw.copy(); S_out["sid"] = [WM.sids[i] for i in S_out["s"]]
    S_out["日期e"] = [str(WM.cal[e].date()) for e in S_out["e"]]
    for c in CELLS:
        kk = {(int(s), int(e)): (x, g, w) for s, e, x, g, w in zip(FB_[c]["s"], FB_[c]["e"], FB_[c]["xpos"], FB_[c]["g"], FB_[c]["why"])}
        S_out[f"{c}_xpos"] = [kk.get((s, e), (np.nan, np.nan, ""))[0] for s, e in zip(S_out["s"], S_out["e"])]
        S_out[f"{c}_g"] = [kk.get((s, e), (np.nan, np.nan, ""))[1] for s, e in zip(S_out["s"], S_out["e"])]
        S_out[f"{c}_why"] = [kk.get((s, e), (np.nan, np.nan, ""))[2] for s, e in zip(S_out["s"], S_out["e"])]
    S_out.to_csv(os.path.join(OUT, "signals.csv.gz"), index=False, float_format="%.10g")
    # ── 主段臂 ──
    arms = []
    for c in CELLS:
        arms.append((f"{c}|b", FB_[c], False, a.reps)); arms.append((f"{c}|r", FR_[c], True, a.reps))
    RES = RL.run_arms(WM, arms, seg, w1, a.procs, log)
    # ── 退化（先寫）──
    DG = {}
    for nm, ms in RES.items():
        h = RL.hold_only(ms, seg)
        DG[nm] = {**h, "探索_退化": RL.degen(h, "探索"), "確認_退化": RL.degen(h, "確認"), "主窗_退化": RL.degen(h, "主窗"), "種子": len(ms)}
    cand = {}
    for c in CELLS:
        g = FB_[c].groupby("e").size()
        cand[c] = {"有進場的日子": int(len(g)), "每個進場日訊號數": RL.q_(g.to_numpy()),
                   "訊號數逐年（進場日）": {str(k): int(v) for k, v in pd.Series([WM.cal[e].year for e in FB_[c]["e"]]).value_counts().sort_index().items()}}
    DJ = {"寫入時間": RL.now_tpe() + "（台北）", "說明": "⭐ 本檔在彙總任何報酬之前寫入（A10、裁定 seq325）；退化 ＝ 平均持股 ＜ 3 或平均現金 ＞ 30%（段內逐日平均、種子中位）；退化格照登錄排除",
          "候選與訊號": cand, "持股與現金": DG,
          "排除的格": sorted({nm.split('|')[0] for nm, v in DG.items() if nm.endswith('|b') and v['探索_退化']})}
    json.dump(DJ, open(os.path.join(OUT, "degeneracy.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    log("[退化] 已寫 degeneracy.json：" + "；".join(f"{k} 探索 {v['探索_平均持股']:.2f} 檔／現金 {v['探索_平均現金']:.1%}、確認 {v['確認_平均持股']:.2f}／{v['確認_平均現金']:.1%}"
                                              f"{'（探索退化）' if v['探索_退化'] else ''}" for k, v in DG.items()))
    # ── 報酬、挑格 ──
    GRID = [{"格": nm.split("|")[0], "版本": nm.split("|")[1], **RL.summarize(ms, Z, seg), **DG[nm]} for nm, ms in RES.items()]
    GR = pd.DataFrame(GRID)
    base = GR[GR["版本"] == "b"].copy(); base["_ord"] = [CELLS.index(c) for c in base["格"]]
    nd = base[~base["探索_退化"]]; all_deg = len(nd) == 0
    pool_ = nd if not all_deg else base
    qq = pool_[pool_["探索_標籤"] == "合格"]
    pick = (qq if len(qq) else pool_).sort_values(["探索_比值", "探索_年化", "_ord"], ascending=[False, False, True]).iloc[0]
    chosen = pick["格"]
    log(f"[挑格] 非退化 {len(nd)}／{len(base)}、探索合格 {len(qq)} ⇒ {chosen}{'（⚠ 全退化）' if all_deg else ''}")
    CH = {v: {k: x for k, x in GR[(GR["格"] == chosen) & (GR["版本"] == v)].iloc[0].to_dict().items() if not k.startswith("_")} for v in ("b", "r")}
    # ── 早年 ──
    EARLYR = early(a, chosen, log)
    lab_c, lab_cr = CH["b"]["確認_標籤"], CH["r"]["確認_標籤"]
    if EARLYR.get("窗"):
        lab_e = EARLYR["格"][f"{chosen}|b"]["早年_標籤"]; lab_er = EARLYR["格"][f"{chosen}|r"]["早年_標籤"]
        if EARLYR["格"][f"{chosen}|b"]["早年_退化"]:
            lab_e = "不可判定（早年退化）"
    else:
        lab_e = lab_er = "不可判定"
    fin_b = RL.stricter(lab_c, lab_e) if lab_e in RL.STRICT else lab_c
    fin_r = RL.stricter(lab_cr, lab_er) if lab_er in RL.STRICT else lab_cr
    tag = lambda L_: ("暫定（事後重切；只進前瞻紀錄）" if L_ == "合格" else L_)
    VERD = {"挑中格": chosen, "全退化": all_deg, "探索": CH["b"]["探索_標籤"], "確認": lab_c, "早年": lab_e, "判定": tag(fin_b),
            "現實版探索": CH["r"]["探索_標籤"], "現實版確認": lab_cr, "現實版早年": lab_er, "現實版判定": tag(fin_r)}
    if all_deg:
        VERD.update({"判定": "全部格退化（照登錄排除）⇒ 沒有可判的格；挑中格數字只作描述", "現實版判定": "同左（全退化）"})
    log(f"[判定] {VERD}")
    # ── 對照與描述 ──
    Fc = FB_[chosen]
    darms = [(f"固定{H}", RL.finalize_rows(WM, RL.fixed_rows(WM, Fc, H), False), False, 50) for H in (20, 60, 120)]
    ma = pd.Series(WM.bench).rolling(200, min_periods=200).mean().to_numpy()
    with np.errstate(invalid="ignore"):
        keep = WM.bench[Fc["e"].to_numpy(int) - 1] > ma[Fc["e"].to_numpy(int) - 1]
    darms.append(("0050在200日線上才買", Fc[keep].reset_index(drop=True), False, 50))
    X1, nu, nm_ = RL.r1_x(WM, log); RL._G["R1X"] = X1
    UR1, _ = RL.universe(WM, log, r1=True)
    if a.smoke:
        UR1 = UR1 & (np.arange(WM.S) % 7 == 0)[:, None]
    SR1, LR1, _ = build_signals(WM, UR1, log)
    SR1 = SR1[(SR1["e"] >= w0) & (SR1["e"] <= w1)].reset_index(drop=True)
    darms.append(("R1排名版", RL.finalize_rows(WM, exit_rows(WM, SR1, T0, chosen), False), False, 50))
    for i in range(a.fake):
        darms.append((f"假訊號#{i}", RL.finalize_rows(WM, RL.fake_rows(WM, Fc, U, i), False), False, ("fake", i)))
    DRES = RL.run_arms(WM, darms, seg, w1, a.procs, log)
    DESC = {nm: {**{k: v for k, v in RL.summarize(ms, Z, seg).items() if not k.startswith("_")}, **RL.hold_only(ms, seg)} for nm, ms in DRES.items() if not nm.startswith("假訊號#")}
    DESC["R1排名版"]["訊號（主窗）"] = int(len(SR1))
    DESC["0050在200日線上才買"]["留下訊號"] = int(keep.sum()); DESC["0050在200日線上才買"]["原訊號"] = int(len(Fc))
    FK = [RL.summarize(ms, Z, seg) for nm, ms in DRES.items() if nm.startswith("假訊號#")]
    FAKE = {}
    for sg in SEGS:
        v = np.array([x[f"{sg}_年化"] for x in FK]); d_ = np.array([x[f"{sg}_回落"] for x in FK])
        FAKE[sg] = {"抽數": len(v), "年化中位": float(np.nanmedian(v)), "年化p10": float(np.nanpercentile(v, 10)), "年化p90": float(np.nanpercentile(v, 90)),
                    "回落中位": float(np.nanmedian(d_)), "p（假訊號年化 ≥ 挑中格）": float(np.mean(v >= CH["b"][f"{sg}_年化"])),
                    "假訊號合格比例": float(np.mean([RL.label(c_, m_, Z[sg])[0] == "合格" for c_, m_ in zip(v, d_)]))}
    # ── 必報 ──
    msC = RES[f"{chosen}|b"]; msR = RES[f"{chosen}|r"]
    TS = {"b": RL.trade_stats(WM, msC, Fc, w1), "r": RL.trade_stats(WM, msR, FR_[chosen], w1)}
    TS_other = {c: RL.trade_stats(WM, RES[f"{c}|b"], FB_[c], w1) for c in CELLS if c != chosen}
    NE = RL.neff_stats(WM, msC[0], seg, log)
    YR = {k: float(np.median([RL.years_ret(m["eq"], WM.cal, w0, w1)[k] for m in msC])) for k in RL.years_ret(msC[0]["eq"], WM.cal, w0, w1)}
    YRr = {k: float(np.median([RL.years_ret(m["eq"], WM.cal, w0, w1)[k] for m in msR])) for k in RL.years_ret(msR[0]["eq"], WM.cal, w0, w1)}
    YR50 = RL.years_ret(WM.bench, WM.cal, w0, w1)
    Y = RL.yl_ref(log); YC = RL.yl_cells()
    R26 = ref26(WM, w0, w1, log); R17 = ref17(log)
    ivA = msC[0]["iv"]
    others = {}
    for fam, nmf in (("fly", "營飆 v1"), ("vol", "營量 v1")):
        others[nmf] = [(s, WM.pos(a_), WM.pos(b_) if b_ != "9999-12-31" else WM.n + 1) for s, a_, b_ in Y[fam]["iv"]]
    others["好營收再加漲停（#26）"] = R26["iv"]; others["好營收股價已認同（#17＋#10）"] = R17["iv"]
    ovl = {}
    for sg, (x_, y_) in seg.items():
        ovl[sg] = {}
        for nmf, ivB in others.items():
            ovl[sg][f"與{nmf}持股重疊率"] = RL.overlap_daily(ivA, ivB, x_, y_)
            ovl[sg][f"{nmf}持股中也在本件的比例（反向）"] = RL.overlap_daily(ivB, ivA, x_, y_)
    VOLS = vol20_share(WM, SIGw)
    SUM = {"meta": {"件": "PREREG高成長加速 seq1", "登錄": regf, "sha": [REG_SHA, REG_SHA2], "讀法寫死": TIME, "run": RL.now_tpe() + "（台北）", "reps": a.reps, "fake": a.fake,
                    "smoke": bool(a.smoke), "版面": {"main": [str(WM.cal[0].date()), str(WM.cal[-1].date()), WM.n, WM.S, WM.n_gate3]},
                    "tw-stock-data": RL._G["sha"], "月營收": {"檔": RL._G["rev_nfiles"], "列": RL._G["rev_nrows"]}, "0050": Z,
                    "成本": {"0.585%版": RL.COST_B, "現實版引擎成本": RL.COST_R}, "化學生技醫療（未剔）股-日（主段母體）": int((OLD & U).sum()),
                    "母體口徑": "20 日均成交金額 ≥ 5,000 萬（事件層原定義）；⚠ 與營量／營飆正式 500 張不同", "本件訊號決策日 20 日均量 ≥ 500 張": VOLS,
                    "減資斷點": "待查（裁定 seq329 §五；本件照現行引擎跑）"},
           "判定": VERD, "挑中格": CH, "退化": DJ, "格": [{k: x for k, x in r.items() if not k.startswith("_")} for r in GRID], "早年": EARLYR,
           "假訊號": FAKE, "描述": DESC, "R1": {"X": X1, "2016-01-04 5,000萬母體（非金融生技）": nu, "同日全市場": nm_, "訊號計數": LR1},
           "逐筆": TS, "逐筆（另一格）": TS_other, "等效獨立": NE, "各年": {"策略": YR, "策略現實版": YRr, "0050": YR50},
           "營量營飆": YC, "營量營飆r0閘": Y["閘"], "#26閘": {"格": R26["格"], "閘": R26["閘"]}, "#17閘": {"格": R17["格"], "閘": R17["閘"]}, "重疊": ovl,
           "訊號計數": LST, "訊號年增": {"本月年增": RL.q_(SIGw["Y"]), "上月年增": RL.q_(SIGw["Yp"])}, "耗時秒": round(time.time() - t00)}
    json.dump(SUM, open(os.path.join(OUT, "summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=lambda o: float(o) if np.isscalar(o) else str(o))
    pd.DataFrame([{k: x for k, x in r.items() if not k.startswith("_")} for r in GRID]).to_csv(os.path.join(OUT, "grid.csv"), index=False, float_format="%.6g")
    seeds = []
    for nm, ms in list(RES.items()) + list(DRES.items()):
        for m in ms:
            seeds.append({"arm": nm, "r": m["r"], **RL.seg_ret(m, seg), **m["hold"], "trades": m["trades"], "lu": m["lu"], "sha": hashlib.sha256(m["eq"].tobytes()).hexdigest()[:16]})
    pd.DataFrame(seeds).to_csv(os.path.join(OUT, "seeds.csv.gz"), index=False, float_format="%.17g")
    pickle.dump({"FB": FB_, "chosen": chosen, "iv0": ivA, "eq0": msC[0]["eq"]}, open(os.path.join(WORK, "run.pkl"), "wb"))
    log(f"[完] {VERD}｜{time.time() - t00:.0f}s")


def early(a, chosen, log):
    """A9：早年段（early 版面）；先依月營收覆蓋決定判定窗（＝ researchRevLimitUp.early 同規則）。"""
    G = RL.load_rev(log)
    try:
        T_, Yc = PRE.coverage(G["rev"], G["rev_ly"])
    except Exception as ex:
        return {"窗": None, "原因": f"覆蓋率算不出：{ex}"}
    ok = {}
    for y, g in Yc[Yc["市場"] == "twse"].groupby("年"):
        ok[int(y)] = bool((g["覆蓋率"] >= 0.90).all())
    yrs = sorted(y for y in ok if 2005 <= y <= 2014)
    start = next((y for y in yrs if all(ok[z] for z in yrs if z >= y)), None)
    cov = {"各年各市場": Yc.to_dict("records"), "判定窗起年": start}
    if start is None:
        return {"窗": None, "原因": "早年各年月營收覆蓋都不到 90%", "覆蓋": cov}
    WE = RL.World("early", a.procs, log)
    ew = (max(f"{start}-01-01", EARLY[0]), EARLY[1])
    ea, eb = WE.segpos(*ew)
    es = {"早年": (ea, eb)}
    ZE = {"早年": RR.bench_row(WE.cal, WE.bench, ea, eb + 1)}
    UE, OLDE = RL.universe(WE, log)
    if a.smoke:
        UE = UE & (np.arange(WE.S) % 7 == 0)[:, None]
    SE, LSE, T0E = build_signals(WE, UE, log)
    SE = SE[(SE["e"] >= ea) & (SE["e"] <= eb)].reset_index(drop=True)
    arms = []; FE = {}
    for c in CELLS:
        rw = exit_rows(WE, SE, T0E, c)
        FE[c] = RL.finalize_rows(WE, rw, False)
        arms.append((f"{c}|b", FE[c], False, a.reps))
        arms.append((f"{c}|r", RL.finalize_rows(WE, rw, True), True, a.reps))
    RE_ = RL.run_arms(WE, arms, es, eb, a.procs, log)
    HE = {nm: RL.hold_only(ms, es) for nm, ms in RE_.items()}
    DJp = os.path.join(OUT, "degeneracy.json")                       # ⭐ 早年也先寫退化、再彙總報酬
    DJ = json.load(open(DJp, encoding="utf-8"))
    DJ["早年"] = {"寫入時間": RL.now_tpe() + "（台北）", "窗": list(ew), **{nm: {**h, "早年_退化": RL.degen(h, "早年")} for nm, h in HE.items()}}
    json.dump(DJ, open(DJp, "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    EG = {}
    for nm, ms in RE_.items():
        EG[nm] = {**{k: v for k, v in RL.summarize(ms, ZE, es).items() if not k.startswith("_")}, **HE[nm], "早年_退化": RL.degen(HE[nm], "早年")}
    msE = RE_[f"{chosen}|b"]
    per = SE["M"]
    out = {"窗": list(ew), "0050": ZE["早年"], "格": EG, "訊號": int(len(SE)), "訊號計數": LSE,
           "IFRS：期別 2013 的訊號占比": float((per.str[:4] == "2013").mean()) if len(per) else np.nan,
           "IFRS：上月年增跨 2013（期別 2013-01～2014-01）占比": float(((per >= "2013-01") & (per <= "2014-01")).mean()) if len(per) else np.nan,
           "各年（策略種子中位）": {k: float(np.median([RL.years_ret(m["eq"], WE.cal, ea, eb)[k] for m in msE])) for k in RL.years_ret(msE[0]["eq"], WE.cal, ea, eb)},
           "各年0050": RL.years_ret(WE.bench, WE.cal, ea, eb), "逐筆": RL.trade_stats(WE, msE, FE[chosen], eb), "覆蓋": cov,
           "化學生技醫療（未剔）股-日": int((OLDE & UE).sum()), "版面": [str(WE.cal[0].date()), str(WE.cal[-1].date()), WE.n, WE.S]}
    log(f"[早年] {ew}：" + "；".join(f"{k} {v['早年_年化']:+.1%}／{v['早年_回落']:+.1%} {v['早年_標籤']}{'（退化）' if v['早年_退化'] else ''}" for k, v in EG.items()))
    return out


# ═════════════ 網頁 ═════════════
def page(a=None):
    S = json.load(open(os.path.join(OUT, "summary.json"), encoding="utf-8"))
    chk = {}
    cf = os.path.join(OUT, "check.json")
    if os.path.exists(cf):
        chk = json.load(open(cf, encoding="utf-8"))
    e = html.escape
    p = lambda x: "—" if x is None or not isinstance(x, (int, float)) or not np.isfinite(x) else f"{x * 100:+.1f}%"
    pp = lambda x: "—" if x is None or not isinstance(x, (int, float)) or not np.isfinite(x) else f"{x * 100:.1f}%"
    V = S["判定"]; ch = V["挑中格"]; Z = S["meta"]["0050"]
    G = {(r["格"], r["版本"]): r for r in S["格"]}
    E = S.get("早年") or {}
    b, r_ = G[(ch, "b")], G[(ch, "r")]
    seg3 = ("探索", "確認", "主窗")

    def cell(x, sg):
        return f"{p(x[f'{sg}_年化'])}／{p(x[f'{sg}_回落'])}<br><span class=m>{x[f'{sg}_標籤']}・持股 {x[f'{sg}_平均持股']:.1f}・現金 {pp(x[f'{sg}_平均現金'])}</span>"

    rows = []
    for (c, v), x in G.items():
        nm = f"{c}{'（挑中）' if c == ch else ''}｜{'0.585% 版' if v == 'b' else '現實版'}"
        eg = (E.get("格") or {}).get(f"{c}|{v}")
        ecell = f"{p(eg['早年_年化'])}／{p(eg['早年_回落'])}<br><span class=m>{eg['早年_標籤']}</span>" if eg else "—"
        rows.append(f"<tr><th>{e(nm)}</th>" + "".join(f"<td>{cell(x, sg)}</td>" for sg in seg3) + f"<td>{ecell}</td></tr>")
    zrow = "<tr class=tot><th>0050</th>" + "".join(f"<td>{p(Z[sg]['cagr'])}／{p(Z[sg]['mdd'])}</td>" for sg in seg3) + \
           f"<td>{p((E.get('0050') or {}).get('cagr'))}／{p((E.get('0050') or {}).get('mdd'))}</td></tr>"
    YC = S["營量營飆"]
    yrows = "".join(f"<tr><th>{e(k)}</th>" + "".join(f"<td>{p(YC[k][sg]['年化'])}／{p(YC[k][sg]['回落'])}<br><span class=m>{YC[k][sg]['標籤']}</span></td>" for sg in seg3) + "</tr>"
                    for k in ("營量 v1", "營飆 v1"))
    diff = "".join(f"<li>{e(k)}：本件 {ch} 年化比它 " + "、".join(f"{sg} {(b[f'{sg}_年化'] - YC[k][sg]['年化']) * 100:+.1f} 點" for sg in seg3) + "</li>" for k in ("營量 v1", "營飆 v1"))
    F = S["假訊號"]
    frows = "".join(f"<tr><th>{sg}</th><td>{p(b[f'{sg}_年化'])}</td><td>{p(F[sg]['年化中位'])}（p10 {p(F[sg]['年化p10'])}～p90 {p(F[sg]['年化p90'])}）</td>"
                    f"<td>{F[sg]['p（假訊號年化 ≥ 挑中格）']:.2f}</td><td>{pp(F[sg]['假訊號合格比例'])}</td></tr>" for sg in seg3)
    D = S["描述"]
    drows = "".join(f"<tr><th>{e(k)}</th>" + "".join(f"<td>{p(x[f'{sg}_年化'])}／{p(x[f'{sg}_回落'])}</td>" for sg in seg3) + "</tr>" for k, x in D.items())
    O = S["重疊"]
    okeys = [k for k in O["主窗"] if not k.endswith("（反向）")]
    orows = "".join(f"<tr><th>{e(k.replace('持股重疊率', '').replace('與', ''))}</th>" + "".join(f"<td>{pp(O[sg][k])}</td>" for sg in seg3)
                    + f"<td>{pp(O['主窗'][k.replace('與', '').replace('持股重疊率', '') + '持股中也在本件的比例（反向）'])}</td></tr>" for k in okeys)
    NE = S["等效獨立"]
    nrows = "".join(f"<tr><th>{sg}</th><td>{x['平均持股']:.1f}</td><td>{x['平均ρ']:.2f}</td><td><b>{x['平均N_eff']:.1f}</b></td><td>{x['最大產業檔數中位']:.0f}（最多 {x['最大產業檔數最大']}）</td>"
                    f"<td>{pp(x['最大產業＞3檔的換股日占比'])}</td></tr>" for sg, x in NE.items())
    TS = S["逐筆"]["b"]
    why = "、".join(f"{e(k)} {v:.1f}" for k, v in TS["出場原因（每顆平均）"].items())
    hd = TS["持有天數（交易日，已出場，種子合計）"]
    yrs = S["各年"]
    yrow = "".join(f"<tr><th>{y}</th><td>{p(yrs['策略'][y])}</td><td>{p(yrs['0050'][y])}</td></tr>" for y in yrs["策略"])
    gates = f"營量營飆 r0 閘 {S['營量營飆r0閘']}；#26 閘 {S['#26閘']}；#17 閘 {S['#17閘']}"
    VS = S["meta"]["本件訊號決策日 20 日均量 ≥ 500 張"]
    head = (f"<p class=lead><b>結論：{e(V['判定'])}。</b>挑中格 {ch}（{'年增轉弱才賣' if ch == 'E1' else '從高點回落 20% 才賣'}）；確認段 {p(b['確認_年化'])}／{p(b['確認_回落'])}"
            f"（{b['確認_標籤']}，0050 {p(Z['確認']['cagr'])}／{p(Z['確認']['mdd'])}）、早年 {e(str(V['早年']))}；現實版判定 {e(V['現實版判定'])}。</p>"
            + (f"<p>挑格照登錄只看探索段（0.585% 版）：" + "、".join(f"{c} {G[(c, 'b')]['探索_標籤']}（比值 {G[(c, 'b')]['探索_比值']:.2f}）" for c in CELLS)
               + f"，0050 比值 {Z['探索']['cagr'] / abs(Z['探索']['mdd']):.2f} ⇒ 挑 {ch}。另一格的確認段數字只作描述、⛔ 不能拿來改判。</p>") +
            "<ul><li>⚠ 抽籤型、多數個股會跌（事件層個股中位 −1.48%）⇒ 要分散買才吃得到平均。</li>"
            "<li>⚠ 多重檢定邊緣（t ≈ 2.8 ＜ 3.38）。</li>"
            "<li>做多那一腿對母體 +1.42%，扣一趟成本後約剩 0.8%；基準是 5,000 萬等權母體、不是 0050。</li>"
            "<li>⚠ 事後重切（事件層結果事前看過）⇒ 就算合格也最多「暫定」、只進前瞻紀錄。⛔ 不是買賣建議。</li>"
            f"<li>母體照事件層原定義（20 日均成交金額 ≥ 5,000 萬），和營量／營飆正式的「20 日均量 ≥ 500 張」不同；本件訊號決策日有 {pp(VS['占比'])} 也過 500 張。</li>"
            "<li>⚠ 減資價格斷點待查（裁定 seq329 §五另案）；本件照現行引擎跑。</li></ul>")
    css = RL_CSS
    doc = (f"<!doctype html><html lang=zh-Hant><head><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'>"
           f"<title>高成長加速</title><style>{css}</style></head><body>"
           f"<h1>高成長加速</h1><p class=m>PREREG高成長加速 seq2（sha {REG_SHA2}；seq1 {REG_SHA} 判定一字未動；裁定 seq329 §三、N_組合 ＋1；必附句 seq328 §二）｜回測線｜停止交易強制出場：開｜產出 {RL.now_tpe()}（台北）</p>"
           + head +
           "<h2>做法（白話）</h2><p>連兩個月營收年增都 ≥ 30%、而且這個月年增比上個月再多 20 個百分點以上 ⇒ 營收公布後第一個交易日開盤買；最多 10 檔等權，候選太多抽籤（200 顆種子取中位）。"
           "出場兩格挑一：E1 之後哪個月年增掉到 30% 以下或比上月少 20 點以上就賣；E2 從持有期最高收盤回落 20% 就賣。成本 0.585%；現實版另加滑價、衝擊、漲跌停買賣不到。</p>"
           "<h2>各格（年化中位／回落中位）</h2><table><thead><tr><th>格</th><th>探索 2017-03～2021-12</th><th>確認 2022-01～2026-08</th><th>主窗</th><th>早年</th></tr></thead><tbody>"
           + "".join(rows) + zrow + "</tbody></table>"
           f"<p class=m>標籤：年化 ＞ 0050 且 年化÷|回落| ≥ 0050 ⇒ 合格；只過年化 ⇒ 另列。退化（平均持股 ＜ 3 或現金 ＞ 30%）的格照登錄排除：{e(', '.join(S['退化']['排除的格']) or '無')}。"
           f"早年窗 {e(str(E.get('窗')))}（月營收覆蓋 ≥ 90% 的年份起）。</p>"
           "<h2>對原策略（營量 v1、營飆 v1）</h2><table><thead><tr><th>策略</th><th>探索</th><th>確認</th><th>主窗</th></tr></thead><tbody>" + yrows + "</tbody></table><ul>" + diff + "</ul>"
           "<h2>假訊號臂（同進場日、同數量、隨機股，200 次）</h2><table><thead><tr><th>段</th><th>本件</th><th>假訊號年化中位</th><th>p</th><th>假訊號合格比例</th></tr></thead><tbody>" + frows + "</tbody></table>"
           "<p class=m>p ＝ 假訊號 200 次裡年化不輸本件的比例。</p>"
           "<h2>持股重疊率（同屬「營收最新變化」一族）</h2><table><thead><tr><th>對方</th><th>探索</th><th>確認</th><th>主窗</th><th>反向（主窗）</th></tr></thead><tbody>" + orows + "</tbody></table>"
           f"<p class=m>本件 r＝0 每天持股裡、同一天也在對方持股裡的比例（逐日平均）；反向 ＝ 對方持股裡也在本件的比例。{e(gates)}</p>"
           "<h2>分散程度</h2><table><thead><tr><th>段</th><th>平均持股</th><th>平均相關 ρ</th><th>等效獨立檔數</th><th>最大產業檔數中位</th><th>同產業 ＞3 檔的換股日</th></tr></thead><tbody>" + nrows + "</tbody></table>"
           f"<h2>逐筆</h2><ul><li>持有天數（交易日）中位 {hd.get('中位', float('nan')):.0f}、平均 {hd.get('平均', float('nan')):.0f}（p10 {hd.get('p10', float('nan')):.0f}～p90 {hd.get('p90', float('nan')):.0f}）。固定天數只描述。</li>"
           f"<li>出場原因（每顆平均筆數）：{why}。</li><li>窗尾（2026-08-24）仍持有 {TS['窗尾仍持有（檔，種子中位）']:.0f} 檔（種子中位）；已持有天數中位 {TS['窗尾仍持有已持有天數'].get('中位', float('nan')):.0f}。</li>"
           f"<li>一年內先跌 15%：{pp(TS['一年內先跌15%比例'])}（{TS['觀察窗滿250筆']} 筆）。</li></ul>"
           "<h2>描述（不判）</h2><table><thead><tr><th>臂</th><th>探索</th><th>確認</th><th>主窗</th></tr></thead><tbody>" + drows + "</tbody></table>"
           "<p class=m>0050 在 200 日線上才買：這個濾網的角色是擋長空頭、不是急跌保護。R1 ＝ 依成交金額排名取前段的母體。</p>"
           "<h2>各年（挑中格、種子中位）</h2><table><thead><tr><th>年</th><th>本件</th><th>0050</th></tr></thead><tbody>" + yrow + "</tbody></table>"
           + (f"<h2>獨立查核</h2><p>{e(chk.get('結論', ''))}</p>" if chk else "")
           + "<p class=m>程式 backtest/researchRevAccel.py；結果 backtest/resultsRevAccel/；讀法在程式檔頭（A1～A16）。</p></body></html>")
    open(PAGE, "w", encoding="utf-8").write(doc)
    print("寫出", PAGE)


RL_CSS = """:root{--bg:#fbfaf7;--fg:#1d1d1b;--mut:#6b6a66;--line:#e2dfd8;--acc:#1f5f8b;--card:#ffffff}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]){--bg:#161615;--fg:#ecebe6;--mut:#a3a19a;--line:#33322f;--acc:#7cb6de;--card:#1e1e1c}}
:root[data-theme="dark"]{--bg:#161615;--fg:#ecebe6;--mut:#a3a19a;--line:#33322f;--acc:#7cb6de;--card:#1e1e1c}
body{background:var(--bg);color:var(--fg);font-family:"Noto Sans TC","PingFang TC","Microsoft JhengHei",sans-serif;line-height:1.6;margin:0;padding:24px 16px;max-width:980px;margin:auto}
h1{font-size:1.5rem;margin:.2em 0}h2{font-size:1.2rem;border-bottom:2px solid var(--acc);padding-bottom:.2em;margin-top:2em}
.lead{font-size:1.08rem}.m{color:var(--mut);font-size:.88rem}
table{border-collapse:collapse;width:100%;margin:.4em 0;font-size:.9rem;display:block;overflow-x:auto;background:var(--card)}
th,td{border:1px solid var(--line);padding:5px 8px;text-align:right;white-space:nowrap}th{text-align:left}thead th{background:var(--line)}tr.tot td,tr.tot th{font-weight:600}"""


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("cmd", choices=["run", "page"])
    ap.add_argument("--procs", type=int, default=2); ap.add_argument("--reps", type=int, default=200); ap.add_argument("--fake", type=int, default=200)
    ap.add_argument("--smoke", action="store_true")
    a = ap.parse_args()
    run(a) if a.cmd == "run" else page(a)


if __name__ == "__main__":
    main()

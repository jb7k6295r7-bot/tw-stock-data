# -*- coding: utf-8 -*-
"""每日名單檔 daily_<資料日>.md（營飆 v1 已達成＋營量 v1 已達成＋營量 v1 即將達成）——回測線，2026-09-28。
依據：市場情報分析線 2109、2130（使用者要每日名單）；裁定 seq270 §四、§五（創新板加標）；seq271 §一（固定註單一寫法、營飆段標題加「（實驗）」）。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.daily_list [--procs 2]
    包裝（fetch main ⇒ archive ⇒ 跑本支 ⇒ 複製到信箱 _營量觀察/）：bash ~/tw-p17/backtest/run_daily_list.sh

⛔ 不寫第二份實作：訊號、營收、5 取 3、去重、即將達成全部呼叫 list_yl13_watch.compute（其營收面板 ＝ list_prereg10.build_panel、AND ＝ research13.and_flags，
   閘：近 20 交易日 AND ＝ list_YL13_2026-09-24）；精簡列 ＝ list_yl13_watch.brief_rows；大盤閘 ＝ list_prereg10.regime_arrays（0050 還原收盤 vs 200 日均）
營飆 v1（PREREG10 #1：AND｜大盤閘｜N10｜H120）已達成 ＝ 資料日當天的 AND 訊號 ∧ 資料日（＝ 進場前一個交易日 t−1）大盤閘開（list_prereg10 L5）；出場 ＝ 第 120 個交易日
營量 v1（#13：AND｜無大盤閘｜N20｜relvol｜H60）已達成 ＝ 資料日當天的 AND 訊號（relvol 大者先）；出場 ＝ 第 60 個交易日（list_yl13 同：D.exit_pos(進場, 60)）
出場日超出資料日曆 ⇒ gate_b_status.future_trading_days 外推（未公告休市只扣週末 ⇒ 實際只會更晚）
創新板 ＝ 名稱含「-創」或「-KY創」⇒ 加標「創新板（限合格投資人）」
輸出 backtest/resultsDaily/daily_<資料日>.md（包裝再複製到信箱 _營量觀察/）

2026-09-30 加（使用者要；協調者轉達；⛔ 原有段落除新增欄以外不變）：
  起漲特徵 ＝ surge_feat_daily（overlap 的 14 個；與 s5work 建表逐格相同，閘 G1）：第一、二節每檔行尾加「｜起漲特徵 N/14」（≥5 個加 ⭐）、第三節表加一欄
  第四節「起漲特徵 ≥10 個（參考，不列入正式挑選）」：當日 ≥10 個的全部股票，依個數排序；張數同第三節算法（3 倍量門檻金額 ÷ 開盤價；8 成）；前 20 個交易日出現過 ≥10 個的標「連續」
  第五節「買賣流程追蹤」：讀 backtest/holdings_flow.txt（代號, 買進日, 買進價），surge_flow_daily 每天從買進日重播；檔案不存在或空 ⇒ 不出這節
    （使用者 2026-09-30：W1 ⇒ 賣 3 成留 7 成；剩 7 成 ＝ 等 W2 或回落 30%（研究定案，commit 075078d9ae）；中段底買回只在出清後；
     全部持有且 W1 未出現、收盤 ≤ 買進價 × 0.85 ⇒ 只加一句參考停損提示、不改流程；
     全部持有期間連 40 個交易日沒創買進後新高 ⇒ 隔天開盤賣全部（使用者定的退場規則，同 restexit R4 乙群 N＝40））
    2026-09-30 晚改（使用者：「你正常不是應該用起漲點來算嗎？」）：流程改從起漲點 t 算（t ＝ 資料日往前 250 日內最高收盤之前的最低收盤日；
     最高收盤、回落 30%、切段、中段底分數、40 天沒新高都從 t 起；W1／W2 只看目前這一段，買進前已出現也算；動作只在買進日之後）；
     每行加「起漲點 t（日期、價）｜目前第幾段｜從 t 起漲幅｜距最高收盤」；買進日 ＝ t 時與舊版逐字相同（閘 G3）
"""
from __future__ import annotations

import argparse
import os
import re
import time

from . import list_yl13_watch as W
from . import list_prereg10 as LP
from . import data as D
from . import gate_b_status as GB
from . import surge_feat_daily as SFD
from . import surge_flow_daily as SFL
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "resultsDaily")
NOTE = "營量 v1 暫定、營飆 v1 實驗（都在實際紀錄觀察中）；看盤參考，照規則收盤成立、隔天開盤才買"          # 裁定 seq271 §一
INNO = "創新板（限合格投資人）"


def tag(name):
    return f"｜{INNO}" if re.search(r"-(?:KY)?創", str(name)) else ""                 # 「-創」或「-KY創」（例 6854 錼創科技-KY創）


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--procs", type=int, default=2); a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    logf = open(os.path.join(OUT, "run.log"), "w", encoding="utf-8"); T0 = time.time()

    def log(m):
        m = f"[{time.time() - T0:5.0f}s] {m}"; print(m, flush=True); logf.write(m + "\n"); logf.flush()
    X = W.compute(a.procs, log)
    A, B, cal, asof, nxt, sha, S = (X[k] for k in ("A", "B", "cal", "asof", "nxt", "sha", "S"))
    n = len(cal)
    bench, ma, reg = LP.regime_arrays(cal)
    gate_on = bool(reg[n - 1])
    fut, basis = GB.future_trading_days(cal, 2 * 120 + 10)
    cal_ext = cal.append(fut)
    e = n                                                      # 進場 ＝ 下一交易日

    def exit_str(H):
        xp = D.exit_pos(e, H)
        b = basis[xp - n]
        return f"{cal_ext[xp].date()}" + ("（未公告休市只扣週末，實際只會更晚）" if "只扣週末" in b else "")
    reason = lambda r: f"營收 {r['營收期別']} 創 24 月新高、強勢 {int(r['分數'])}/5（{r['已達成']}）"
    # ── 起漲特徵（surge_feat_daily）
    DATA = os.path.expanduser(f"~/h2data/{sha}/data"); AUX = SFD.ensure_aux(sha)
    flows = SFL.read_flow()
    Wf, unif = SFD.world(DATA, AUX, SFD.EARLY)
    d0 = n - 1 - 20
    if flows:
        d0 = min(d0, n - 1 - 250)                                     # 起漲點 t 在資料日往前 250 日內
    for c_, bd_, bp_ in flows:
        e_ = int(cal.searchsorted(pd.Timestamp(bd_)))
        d0 = min(d0, max(e_ - 250, 0))                                # 買進日早於 t ⇒ 買進日往前 250 日內
    R = SFD.compute(DATA, AUX, d0, n - 1, W=Wf, uni=unif, procs=a.procs, log=log)
    has, cnt = SFD.feat14(R); T = n - 1 - R["d0"]
    CNT = dict(zip(unif["stock_id"], cnt[:, T])); BARD = dict(zip(unif["stock_id"], R["bar"][:, T]))

    def sf(sid):
        v = CNT.get(str(sid)); b = BARD.get(str(sid))
        return "｜起漲特徵 —" if v is None or not b else f"｜起漲特徵 {int(v)}/14{' ⭐' if v >= 5 else ''}"
    L = [f"# 每日名單 {asof}（資料日）", "",
         f"- commit：tw-stock-data main {sha[:10]}｜資料日 {asof}｜下一交易日 {nxt[0].date()}（外推）",
         f"- 營飆大盤閘（前一天 0050 在 200 日線上）：{'開' if gate_on else '關'}（{asof} 0050 還原收盤 {bench[n - 1]:.2f}、200 日線 {ma[n - 1]:.2f}）", "",
         f"## 一、營飆 v1（實驗）已達成（{nxt[0].date()} 開盤照規則買；最多 10 檔、候選多於空槽時抽籤）", ""]
    if gate_on and len(A):
        L += [f"- {r['代號']} {r['名稱']}{tag(r['名稱'])}｜{reason(r)}｜出場 {exit_str(120)}（第 120 個交易日收盤）{sf(r['代號'])}" for r in A.sort_values("代號").to_dict("records")]
    else:
        L.append("- 無" + ("（大盤閘關：今天的營收＋強勢訊號照規則不進場）" if (not gate_on and len(A)) else ""))
    L += ["", f"## 二、營量 v1 已達成（{nxt[0].date()} 開盤照規則買；20 檔、候選多於空槽時 relvol 大者先）", ""]
    if len(A):
        L += [f"- {r['代號']} {r['名稱']}{tag(r['名稱'])}｜{reason(r)}｜relvol 第 {int(r['relvol 排名'])}｜出場 {exit_str(60)}（第 60 個交易日收盤）{sf(r['代號'])}" for r in A.to_dict("records")]
    else:
        L.append("- 無")
    ar, br = W.brief_rows(A, B)
    L += ["", "## 三、營量 v1 即將達成（最有可能的幾檔；兩天內可能、沒被去重擋住）", "",
          "張數 ＝ 3 倍量門檻金額 ÷（最新收盤 ×（1＋開高幅度））；「8 成」＝ 該張數 × 0.8。", "",
          "| 代號 名稱 | 門檻（億） | 平盤開 張（8 成） | 開高 3% 張（8 成） | 開高 5% 張（8 成） | 還差的價格條件 | 另一條路 | 起漲特徵 |", "|---|---|---|---|---|---|---|---|"]
    for r in br:
        L.append(f"| {r['代號']} {r['名稱']}{tag(r['名稱'])} | {r['門檻（億）']:.1f} | {r['平盤開 張']:,}（{r['平盤開 8 成']:,}） | {r['開高 3% 張']:,}（{r['開高 3% 8 成']:,}） | "
                 f"{r['開高 5% 張']:,}（{r['開高 5% 8 成']:,}） | {r['還差的價格條件']} | {r['另一條路']} | {sf(r['代號'])[6:]} |")
    if not br:
        L.append("| 無 | | | | | | | |")
    # ── 四、起漲特徵 ≥10 個
    L += ["", "## 四、起漲特徵 ≥10 個（參考，不列入正式挑選）", "",
          "14 個起漲特徵（飆股回推 seq6 overlap 那 14 個）當天收盤同時符合 10 個以上的全部股票；⭐ ＝ 第一～三節裡符合 ≥5 個的。",
          "張數同第三節算法：3 倍量門檻金額（前 20 個交易日平均成交額 × 3，不含當天）÷（最新收盤 ×（1＋開高幅度））；「8 成」＝ 該張數 × 0.8。「連續」＝ 前 20 個交易日內也出現過 ≥10 個。", "",
          "| 代號 名稱 | 收盤 | 個數 | 缺哪幾個 | 平盤開 張（8 成） | 開高 3% 張（8 成） | 開高 5% 張（8 成） | 連續 |", "|---|---|---|---|---|---|---|---|"]
    top = [(int(cnt[i, T]), unif.loc[i, "stock_id"], i) for i in range(len(unif)) if R["bar"][i, T] and cnt[i, T] >= 10]
    D.DATA = DATA
    for k_, sid, i in sorted(top, key=lambda x: (-x[0], x[1])):
        st = D.load_stock(sid, unif.loc[i, "market"], cal); amt = pd.to_numeric(st.df["amount"], errors="coerce").to_numpy(float)
        raw = pd.read_csv(os.path.join(DATA, "stocks", sid + ".csv"), dtype={"date": str}, usecols=["date", "close"]).drop_duplicates("date").set_index("date")["close"]
        rc = float(pd.to_numeric(raw.get(str(cal[n - 1].date())), errors="coerce"))
        bidx = np.flatnonzero(np.isfinite(amt[: n - 1])); th = float(np.mean(amt[bidx[-20:]])) * 3 if len(bidx) >= 20 else np.nan
        lots = [th / (rc * (1 + g)) / 1000 if np.isfinite(th) and rc > 0 else np.nan for g in (0.0, 0.03, 0.05)]
        miss = "、".join(SFD.SHORT[j] for j in range(14) if not has[i, T, j])
        cont = "連續" if (cnt[i, max(T - 20, 0):T] >= 10).any() and T >= 1 else ""
        nm = str(unif.loc[i, "name"])
        L.append(f"| {sid} {nm}{tag(nm)} | {rc:,.2f} | {k_} | {miss or '—'} | " + " | ".join(f"{int(v):,}（{int(v * 0.8):,}）" if np.isfinite(v) else "—" for v in lots) + f" | {cont} |")
    if not top:
        L.append("| 無 | | | | | | | |")
    # ── 五、買賣流程追蹤
    if flows:
        names_bj = SFL.bj_scorer()
        L += ["", "## 五、買賣流程追蹤（你買進的；每天從起漲點 t 重播，動作只在買進日之後）", "",
              "起漲點 t ＝ 資料日往前 250 個交易日內「最高收盤之前的最低收盤日」；最高收盤、回落 30%、切段、中段底分數、40 天沒新高都從 t 起算；W1／W2 只看目前這一段（買進前已出現也算）；−15% 參考提示仍以你的買進價為準。",
              f"流程：全部持有 →（W1 還沒出現前，連續 40 個交易日沒創新高 ⇒ 隔天開盤賣全部，結束）→（W1 第一頂警示，隔天開盤賣 3 成、留 7 成）→ 已賣 3 成 →（剩 7 成：等 W2 第二頂警示〔再次處置或出關〕或從最高回落 30%，隔天開盤賣）→ 已出清／待買回 →"
              f"（從最高回落 20% 且中段底分數 ≥ {names_bj[1]}，隔天開盤買回）→ 第二段持有 →（W2，隔天開盤賣）→ 結束；任何時候從最高回落 30% ＝ 本筆結束。", ""]
        for c_, bd_, bp_ in flows:
            o_ = SFL.replay(R, c_, bd_, bp_, DATA, AUX, names_bj)
            if "錯誤" in o_:
                L.append(f"- {c_}｜買進 {bd_} {bp_:g}｜⚠ {o_['錯誤']}"); continue
            far_ = "" if not np.isfinite(o_["距最高"]) else f"｜距最高收盤 {o_['距最高'] * 100:.1f}%"
            tp_ = "" if o_.get("起漲點價") is None else f" {o_['起漲點價']:g}"
            anc_ = f"｜起漲點 t {o_['起漲點']}{tp_}{o_.get('錨點說明', '')}｜目前第 {o_['目前第幾段']} 段｜從 t 起漲幅 {o_['從起漲漲幅'] * 100:+.1f}%"
            L.append(f"- {o_['代號']} {o_['名稱']}{tag(o_['名稱'])}｜買進 {bd_} {bp_:g}{anc_}｜階段：{o_['階段']}｜今日訊號：{o_['今日訊號']}｜**今天收盤後：{o_['今天收盤後該做什麼']}**{('｜' + o_['參考']) if o_.get('參考') else ''}{far_}｜歷程：{o_['歷程']}")
    L += ["", NOTE, ""]
    fn = os.path.join(OUT, f"daily_{asof}.md")
    open(fn, "w", encoding="utf-8").write("\n".join(L))
    log(f"[完] {fn}｜大盤閘 {'開' if gate_on else '關'}｜營量已達成 {list(A['代號']) if len(A) else []}｜即將達成 {[r['代號'] for r in br]}｜閘 {S['閘（近 20 交易日 AND 訊號 ＝ list_YL13_2026-09-24）']['過']}")
    print(fn)


if __name__ == "__main__":
    main()

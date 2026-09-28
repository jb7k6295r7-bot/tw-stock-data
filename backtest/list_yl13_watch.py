# -*- coding: utf-8 -*-
"""營量 v1「即將達成」觀察名單（使用者 09-28 原話：「有可以提早一或二天給我即將達成門檻的個股嗎？然後跟我說達成的門檻是什麼！」）。
⛔ 只是描述性名單：不是新策略、不做回測判定、N 不加；網頁頂端逐字寫明「觀察名單，不是買進建議…」。回測線，2026-09-28。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.list_yl13_watch [--procs 2]
    簡短查核：~/tw-p16/.venv/bin/python backtest/list_yl13_watch_check.py

═══ 資料 ═══
  tw-stock-data 最新 main（git archive 到 ~/h2data/<sha>/data，唯讀：adj、meta、mops/revenue_hist、stocks、stocks_per）；⛔ 不用 edc6f 快照
  ⚠ 最新 main 的最後交易日仍是 2026-09-24（09-25 中秋、09-28 教師節休市；次一交易日由 gate_b_status.future_trading_days 外推）
═══ 營量 v1 訊號（照原件，⛔ 不改定義）═══
  營收半：list_prereg10.build_panel（research34.process_stock，liq_mode=shares、pub_day=10、窗尾延到日曆最後一根）；
          AND ＝ research13.and_flags：訊號根當下最新一期面板列（signal_pos ≤ pos、距離 ≤ 45 個交易日）rev_hi24
          （rev_hi24 ＝ 當期月營收 ≥ 前 24 期最高，24 期都要有值；面板列要過 research34 的 gate：流動性、處置、斷點窗）
  技術半（research11.stock_features 主格 MAIN_CELL c1＝0.30、c3＝3.0、去重 20；有效 K 棒、還原價）：
    c1 近 20 日漲幅 ret20 ＝ 收盤 ÷ 20 根前收盤 − 1 ≥ 30%
    c2 nup20 ＝ 近 20 根有效 K 棒中「收盤漲停」的根數 ≥ 3（漲停 ＝ 未還原收盤 ＝ research11.limit_price(前一根未還原收盤, 漲, 10%)，
       2015-06 前 7%；還原事件日與上市前 5 根不判）
    c3 amt_ratio ＝ 當根成交金額 ÷ 前 20 根成交金額平均（不含當根）≥ 3
    c4 收盤 ＞ MA100（含當根 100 根均）
    c5 收盤 ≥ 近 250 根最高收盤（含當根）
    eligible ＝ 第 250 根起、非 skip、MA100 與 amt_ratio 有值、訊號根與前 20 根無壞根；5 取 3 ＝ eligible ∧ 分數 ≥ 3；
    同檔 20 根去重（k − 上一個保留 k ＞ 20；去重在 5 取 3 事件上、先於營收條件）⇒ AND 保留者 ＝ 訊號；隔天開盤買；relvol 大者先
  閘：本程式用最新資料重算到 2026-09-24 的 AND 訊號（近 20 交易日）＝ resultsList/list_YL13_2026-09-24.csv（代號、訊號日）
═══ 三區（最新交易日收盤後）═══
  A 今天已達成：AND ∧ 分數 ≥ 3 ∧ 去重保留 ⇒ 次一交易日開盤可買；relvol 排名
  B 差一個條件：營收條件成立（今天、且次一交易日仍在 45 日內）∧ eligible ∧ 分數 ＝ 2；
    未達成條件的「明天收盤要到多少」（本線讀法，⭐ 看名單前寫定）：
      c1 明天收盤 ≥ 1.30 × 第 k−19 根收盤（明天的 20 根前）
      c4 明天收盤 ＞ （近 99 根收盤和）÷ 99（＝ 明天的 MA100 門檻）
      c5 明天收盤 ≥ 近 249 根最高收盤
      c3 明天成交金額 ≥ 3 × 近 20 根（含今天）成交金額平均
      c2 近 19 根漲停數 ＋ 明天漲停 ≥ 3：差 1 次 ⇒ 明天收漲停（價 ＝ 漲停價）；差 ≥ 2 次 ⇒ 明天做不到
    明天分數（價格條件 c1／c2／c4／c5 都隨收盤價單調）⇒「不靠量」最低所需收盤（價格條件湊滿 3）、「靠量」最低所需收盤（量達 c3 時價格條件湊滿 2）
    所需漲幅 ＝ 所需收盤 ÷ 今天收盤 − 1；明天上限 ＝ 漲停價；排序 ＝ 兩者較小
    ⚠ 今天已成立的條件明天可能掉（例：20 根前的價位換了、c3 是單日條件）⇒ 一併寫出「明天維持所需」
    「兩天內可能」（本線讀法）：所需漲幅 ≤ 21%（約兩根漲停）且 方向合理 ＝ 近 5 日報酬 ＞ 0 且 收盤 ＞ MA20
    去重：20 根內已有 5 取 3 事件 ⇒ 明天就算湊滿也不出訊號（標「去重擋住」、排在後面）
  C 技術面已 ≥ 3 分（eligible）、但營收條件不成立：最新一期營收距前 24 期最高差多少 %、下期需達多少、下次公布法定期限（次月 10 日）
輸出 backtest/resultsYLwatch/：watch_A.csv、watch_B.csv、watch_C.csv、summary.json、REPORT.md、營量v1_即將達成_<日>.html
"""
from __future__ import annotations

import argparse
import html
import json
import os
import subprocess
import time
from multiprocessing import Pool

import numpy as np
import pandas as pd

from . import list_prereg10 as LP           # ⛔ 只 import（import 時會指向 edc6f；下面改指最新 main）
from . import data as D
from . import research11 as R
from . import research13 as R13
from . import research34 as R34
from . import gate_b_status as GB
from . import chart_svg as CS

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "resultsYLwatch")
REPO = os.path.dirname(HERE)
C1, C3, DD = 0.30, 3.0, 20
TOP = ("觀察名單，不是買進建議；提早買進（早鳥）過去測過沒有比等訊號好（回測 研究十二）；營量 v1 規則是訊號成立後隔天開盤買")
_G: dict = {}


def feat(args):
    sid, mk = args
    cal = _G["cal"]; n = len(cal)
    B = R.load_bars(sid, mk, cal)
    if B is None:
        return sid, None
    idx, c, o, amt, rc, up, skip, nb = (B[k] for k in ("idx", "c", "o", "amt", "rc", "up", "skip", "next_bad"))
    nn = len(idx); ar = np.arange(nn)
    ret20 = np.array(c / np.roll(c, 20) - 1, dtype=float); ret20[:20] = np.nan
    nup20 = pd.Series(up.astype(int)).rolling(20, min_periods=20).sum().to_numpy(float)
    ap20 = np.array(R._roll_mean(np.roll(amt, 1), 20), dtype=float); ap20[:21] = np.nan
    with np.errstate(invalid="ignore", divide="ignore"):
        ar_ = amt / ap20
    ma20 = R._roll_mean(c, 20); ma100 = R._roll_mean(c, 100); hi250 = R._roll_max(c, 250)
    nb_sig = nb[np.maximum(ar - 20, 0)]
    elig = (ar >= 249) & ~skip & ~np.isnan(ma100) & ~np.isnan(ar_) & (nb_sig > ar)
    with np.errstate(invalid="ignore"):
        cs = np.c_[ret20 >= C1, nup20 >= 3, ar_ >= C3, c > ma100, c >= hi250]
    score = cs.sum(1)
    cand = np.flatnonzero(elig & (score >= 3))
    picks = []; last = -10 ** 9
    for k in cand:
        if k - last > DD:
            picks.append(int(k)); last = k
    out = {"picks": [(k, int(idx[k])) for k in picks], "n_bars": nn}
    k = nn - 1
    if int(idx[k]) != n - 1 or k < 260:
        return sid, out
    med = float(np.nanmedian(amt[k - 60:k]))
    relvol = float(amt[k]) / med if med > 0 and np.isfinite(amt[k]) else np.nan
    fac = c[k] / rc[k] if rc[k] > 0 else np.nan
    lim_up = R.limit_price(float(rc[k]), True, 0.10) * fac                       # 明天漲停價（還原尺度）
    s19 = int(up[k - 18:k + 1].sum())
    t1 = 1.30 * c[k - 19]
    t4 = float(c[k - 98:k + 1].sum()) / 99.0
    t5 = float(c[k - 248:k + 1].max())
    a3 = 3.0 * float(np.mean(amt[k - 19:k + 1]))
    kl = picks[-1] if picks else -10 ** 9
    out["last"] = {"k": k, "pos": int(idx[k]), "close": float(c[k]), "raw_close": float(rc[k]), "fac": float(fac), "open": float(o[k]),
                   "ret20": float(ret20[k]), "nup20": float(nup20[k]), "amt": float(amt[k]), "amt_prev20": float(ap20[k]), "amt_ratio": float(ar_[k]),
                   "ma100": float(ma100[k]), "hi250": float(hi250[k]), "ma20": float(ma20[k]), "ret5": float(c[k] / c[k - 5] - 1),
                   "c_k20": float(c[k - 20]), "cond": [bool(x) for x in cs[k]], "score": int(score[k]), "elig": bool(elig[k]), "relvol": relvol,
                   "picked_today": bool(picks and picks[-1] == k), "last_pick_k": int(kl), "dedup_block_tmr": bool((k + 1) - kl <= DD),
                   "t1": float(t1), "t4": float(t4), "t5": float(t5), "a3": float(a3), "s19": s19, "lim_up": float(lim_up)}
    return sid, out


def tomorrow(L):
    """明天：價格條件門檻 ⇒ 不靠量／靠量 的最低所需收盤。"""
    th = {"c1": L["t1"], "c4": L["t4"] * (1 + 1e-9), "c5": L["t5"]}
    if L["s19"] >= 3:
        c2 = 0.0                                  # 明天不論漲跌都成立
    elif L["s19"] == 2:
        c2 = L["lim_up"]
    else:
        c2 = np.inf
    th["c2"] = c2
    v = sorted(th.values())
    p_novol = v[2] if v[2] <= L["lim_up"] + 1e-9 else np.nan                 # 價格條件湊滿 3
    p_vol = v[1] if v[1] <= L["lim_up"] + 1e-9 else np.nan                   # 量達 c3 時價格條件湊滿 2
    return th, p_novol, p_vol


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--procs", type=int, default=2); a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    logf = open(os.path.join(OUT, "run.log"), "w", encoding="utf-8"); T0 = time.time()

    def log(m):
        m = f"[{time.time() - T0:5.0f}s] {m}"; print(m, flush=True); logf.write(m + "\n"); logf.flush()
    sha = subprocess.run(["git", "-C", REPO, "rev-parse", "origin/main"], capture_output=True, text=True).stdout.strip()
    DATA = os.path.expanduser(f"~/h2data/{sha}/data")
    if not os.path.isdir(DATA):
        raise SystemExit(f"⛔ 沒有 {DATA}（先 git archive 最新 main）")
    D.DATA = DATA
    cal = D.load_calendar(); n = len(cal); asof = str(cal[-1].date())
    nxt = GB.future_trading_days(cal, 2)[0]
    log(f"===== list_yl13_watch｜main {sha[:10]}｜最新交易日 {asof}｜次一交易日 {nxt[0].date()}（外推）=====")
    S = {"資料": {"main": sha, "最新交易日": asof, "次一交易日（外推）": str(nxt[0].date()), "再次一": str(nxt[1].date())}, "說明": TOP}
    stocks, uni = LP.universe()
    panel, rdates, _ = LP.build_panel(cal, uni, log)
    pnl = panel.copy(); pnl["rev_hi24"] = pnl["rev_hi24"].fillna(False).astype(bool)
    _G["cal"] = cal
    with Pool(a.procs, initializer=R._init, initargs=(cal,)) as pool:
        FT = dict(pool.map(feat, list(zip(uni["stock_id"], uni["market"])), chunksize=8))
    log(f"[技術] {sum(v is not None for v in FT.values())} 檔")
    # 全部 5 取 3 事件 ⇒ AND
    Sx = pd.DataFrame([(s, k, p) for s, v in FT.items() if v for k, p in v["picks"]], columns=["sid", "k", "pos"])
    flags, _ = R13.and_flags(Sx, pnl)
    AND = Sx[flags].copy(); AND["date"] = [str(cal[p].date()) for p in AND["pos"]]
    # 閘
    ref = pd.read_csv(os.path.join(HERE, "resultsList", "list_YL13_2026-09-24.csv"), dtype={"stock_id": str})
    mine = AND[AND["pos"] >= n - 20]
    A_ = set(zip(ref["stock_id"], ref["signal_date"])); B_ = set(zip(mine["sid"], mine["date"]))
    S["閘（近 20 交易日 AND 訊號 ＝ list_YL13_2026-09-24）"] = {"既有": len(A_), "本程式": len(B_), "只在既有": sorted(A_ - B_), "只在本程式": sorted(B_ - A_), "過": A_ == B_}
    ext = pd.read_csv(os.path.join(HERE, "resultsList", "and_signals_ext.csv.gz"), dtype={"sid": str}, usecols=["sid", "pos"])
    edc = pd.read_csv(os.path.join(os.path.expanduser("~/h2data/edc6f8002fed8803795e3486ad57db513f7e9f65/data/meta/calendar_twse.csv")))["date"].tolist()
    E_ = set(zip(ext["sid"], [edc[p] for p in ext["pos"]])); M_ = set(zip(AND["sid"], AND["date"]))
    S["對帳（全期 AND ＝ and_signals_ext；描述）"] = {"既有": len(E_), "本程式": len(M_), "只在既有": len(E_ - M_), "只在本程式": len(M_ - E_),
                                                "只在既有（前 10）": sorted(E_ - M_)[:10], "只在本程式（前 10）": sorted(M_ - E_)[:10]}
    log(f"[閘] {S['閘（近 20 交易日 AND 訊號 ＝ list_YL13_2026-09-24）']}｜全期對帳 {S['對帳（全期 AND ＝ and_signals_ext；描述）']}")
    # 營收狀態（每檔最新面板列）
    lastrow = pnl[pnl["signal_pos"] <= n - 1].sort_values("signal_pos").groupby("stock_id").tail(1).set_index("stock_id")
    rev, _, _ = R34.load_revenue()
    avail = [p for p in rev.index if p in rdates and rdates[p][0] <= n - 1]
    name = stocks.drop_duplicates("stock_id").set_index("stock_id")["name"]; mkt = stocks.drop_duplicates("stock_id").set_index("stock_id")["market"]

    def revstat(s):
        r = lastrow.loc[s] if s in lastrow.index else None
        ok_today = bool(r is not None and r["rev_hi24"] and (n - 1 - int(r["signal_pos"])) <= R13.STALE_MAX)
        ok_tmr = bool(r is not None and r["rev_hi24"] and (n - int(r["signal_pos"])) <= R13.STALE_MAX)
        d = {"營收成立（今天）": ok_today, "營收成立（明天）": ok_tmr, "營收期別": (r["period"] if r is not None else None),
             "面板距今（交易日）": (int(n - 1 - int(r["signal_pos"])) if r is not None else None)}
        if s in rev.columns:
            col = rev[s]
            ps = [p for p in avail if np.isfinite(col.get(p, np.nan))]
            if ps:
                p = ps[-1]; i = list(rev.index).index(p)
                prev = col.iloc[max(0, i - 24):i]
                h24 = float(prev.max()) if len(prev) == 24 and prev.notna().all() else np.nan
                nxt_h = float(col.iloc[max(0, i - 23):i + 1].max()) if col.iloc[max(0, i - 23):i + 1].notna().all() else np.nan
                d.update({"最新可用營收期": p, "最新營收": float(col[p]), "前24期最高": h24, "距24期高": (float(col[p]) / h24 - 1) if h24 > 0 else np.nan,
                          "下期需達（≥ 近 24 期最高）": nxt_h, "下期需月增": (nxt_h / float(col[p]) - 1) if col[p] > 0 else np.nan})
        if ok_today:
            why = ""
        elif r is None:
            why = "營收面板沒有這檔的列（未過 research34 gate 或無營收）"
        elif (n - 1 - int(r["signal_pos"])) > R13.STALE_MAX:
            why = f"最新面板列 {r['period']} 距今 {n - 1 - int(r['signal_pos'])} 日 ＞ 45"
        elif d.get("最新可用營收期") and d["最新可用營收期"] != r["period"]:
            why = f"最新營收 {d['最新可用營收期']} 那期的面板列被 gate 擋（處置／流動性／斷點窗），沿用 {r['period']}（未創高）"
        else:
            why = f"{r['period']} 未創 24 月新高"
        d["營收未成立原因"] = why
        y, m = int(asof[:4]), int(asof[5:7])
        d["下次公布法定期限"] = f"{y}-{m + 1:02d}-10" if m < 12 else f"{y + 1}-01-10"
        return d
    A, B, C = [], [], []
    for s, v in FT.items():
        if not v or "last" not in v:
            continue
        L = v["last"]
        if not L["elig"]:
            continue
        rs = revstat(s)
        base = {"代號": s, "名稱": str(name.get(s, "")), "市場": str(mkt.get(s, "")), "收盤": L["raw_close"], "分數": L["score"],
                "c1 近20日漲幅": L["ret20"], "c2 近20根漲停數": L["nup20"], "c3 成交額倍數": L["amt_ratio"], "c4 收盤÷MA100": L["close"] / L["ma100"],
                "c5 收盤÷250日高": L["close"] / L["hi250"], "已達成": "".join(f"c{i + 1}" for i in range(5) if L["cond"][i]),
                "relvol": L["relvol"], **rs, "_L": L}
        if L["score"] >= 3 and rs["營收成立（今天）"] and L["picked_today"]:
            A.append(base)
        elif L["score"] == 2 and rs["營收成立（今天）"] and rs["營收成立（明天）"]:
            th, pnv, pv = tomorrow(L)
            fr = L["fac"]
            best = np.nanmin([pnv, pv]) if np.isfinite([pnv, pv]).any() else np.nan
            base.update({"明天門檻 c1（收盤≥）": th["c1"] / fr, "明天門檻 c4（收盤＞）": L["t4"] / fr, "明天門檻 c5（收盤≥）": th["c5"] / fr,
                         "明天門檻 c2": ("已滿 3 次" if L["s19"] >= 3 else (f"差 1 次：明天收漲停 {L['lim_up'] / fr:.2f}" if L["s19"] == 2 else f"差 {3 - L['s19']} 次：明天做不到")),
                         "明天門檻 c3（成交額≥，元）": L["a3"], "明天漲停價": L["lim_up"] / fr,
                         "不靠量所需收盤": (pnv / fr) if np.isfinite(pnv) else np.nan, "不靠量所需漲幅": (pnv / L["close"] - 1) if np.isfinite(pnv) else np.nan,
                         "靠量所需收盤": (pv / fr) if np.isfinite(pv) else np.nan, "靠量所需漲幅": (pv / L["close"] - 1) if np.isfinite(pv) else np.nan,
                         "所需漲幅（排序）": (best / L["close"] - 1) if np.isfinite(best) else np.inf,
                         "方向合理": bool(L["ret5"] > 0 and L["close"] > L["ma20"]), "去重擋住": L["dedup_block_tmr"]})
            base["兩天內可能"] = bool(np.isfinite(base["所需漲幅（排序）"]) and base["所需漲幅（排序）"] <= 0.21 and base["方向合理"] and not L["dedup_block_tmr"])
            B.append(base)
        elif L["score"] >= 3 and not rs["營收成立（今天）"]:
            C.append(base)
    A = pd.DataFrame(A); B = pd.DataFrame(B); C = pd.DataFrame(C)
    if len(A):
        A = A.sort_values("relvol", ascending=False).reset_index(drop=True); A.insert(0, "relvol 排名", np.arange(1, len(A) + 1))
    if len(B):
        B = B.sort_values(["去重擋住", "所需漲幅（排序）", "代號"]).reset_index(drop=True)
    if len(C):
        C = C.sort_values(["距24期高", "代號"], ascending=[False, True]).reset_index(drop=True)
    for nm, T_ in (("A", A), ("B", B), ("C", C)):
        T_.drop(columns=[c for c in T_.columns if c.startswith("_")]).to_csv(os.path.join(OUT, f"watch_{nm}.csv"), index=False, encoding="utf-8-sig", float_format="%.12g")
    S["筆數"] = {"A 今天已達成": len(A), "B 差一個條件": len(B), "B 其中兩天內可能": int(B["兩天內可能"].sum()) if len(B) else 0,
               "B 其中去重擋住": int(B["去重擋住"].sum()) if len(B) else 0, "C 技術已達成、營收未成立": len(C)}
    log(f"[名單] {S['筆數']}")
    page(A, B, C, cal, asof, nxt, sha, S)
    json.dump(S, open(os.path.join(OUT, "summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    R_ = [f"# 營量 v1 即將達成觀察名單（{asof} 收盤後）", "", f"> {TOP}", "", f"- 資料：tw-stock-data main {sha[:10]}；最新交易日 {asof}；次一交易日 {nxt[0].date()}（外推）",
          f"- 閘：{json.dumps(S['閘（近 20 交易日 AND 訊號 ＝ list_YL13_2026-09-24）'], ensure_ascii=False)}",
          f"- 全期對帳（描述）：{json.dumps(S['對帳（全期 AND ＝ and_signals_ext；描述）'], ensure_ascii=False)}", f"- 筆數：{json.dumps(S['筆數'], ensure_ascii=False)}", "",
          "讀法見程式開頭（c2 定義、明天門檻、兩天內可能、去重）。"]
    open(os.path.join(OUT, "REPORT.md"), "w", encoding="utf-8").write("\n".join(R_) + "\n")
    log(f"[完] {S['閘（近 20 交易日 AND 訊號 ＝ list_YL13_2026-09-24）']['過']}")


def page(A, B, C, cal, asof, nxt, sha, S):
    P = lambda x: "—" if x is None or (isinstance(x, float) and not np.isfinite(x)) else f"{x * 100:+.1f}%"
    F2 = lambda x: "—" if x is None or (isinstance(x, float) and not np.isfinite(x)) else f"{x:.2f}"
    CSS = open(os.path.join(HERE, "list_yl13_hist.py"), encoding="utf-8").read().split('CSS = """')[1].split('"""')[0] + \
        "\ntd.l,th.l{text-align:left}th{cursor:pointer;white-space:nowrap}.ok{color:#2e7d32}.no{color:#c62828}.pick{background:#fff4cc}"
    JS = """<script>document.querySelectorAll('table.s').forEach(function(t){t.querySelectorAll('th').forEach(function(h,i){h.addEventListener('click',function(){
var b=t.tBodies[0],r=Array.from(b.rows),d=h.dataset.d==='1'?-1:1;h.dataset.d=d===1?'1':'0';
r.sort(function(x,y){var a=x.cells[i].dataset.v,c=y.cells[i].dataset.v;var na=parseFloat(a),nc=parseFloat(c);
if(!isNaN(na)&&!isNaN(nc))return (na-nc)*d;return (a||'').localeCompare(c||'')*d;});r.forEach(function(z){b.appendChild(z)});});});});</script>"""

    def conds(L):
        items = [("c1 20日漲", L["ret20"], "≥ +30%", P(L["ret20"])), ("c2 漲停數", L["nup20"], "≥ 3", f"{L['nup20']:.0f}"),
                 ("c3 成交額倍數", L["amt_ratio"], "≥ 3", f"{L['amt_ratio']:.2f}"), ("c4 收÷MA100", L["close"] / L["ma100"], "＞ 1", f"{L['close'] / L['ma100']:.3f}"),
                 ("c5 收÷250日高", L["close"] / L["hi250"], "≥ 1", f"{L['close'] / L['hi250']:.3f}")]
        return " ".join(f"<span class='{'ok' if L['cond'][i] else 'no'}'>{'✔' if L['cond'][i] else '✘'}{nm} {v}（{th}）</span>" for i, (nm, _, th, v) in enumerate(items))
    H = ['<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">',
         f"<title>營量 v1 即將達成 {asof}</title>", f"<style>{CSS}</style></head><body><main>",
         f"<h1>營量 v1 即將達成觀察名單（{asof} 收盤後）</h1>", f"<p class='lead'><b>{html.escape(TOP)}</b></p>",
         f"<p class='note'>次一交易日 {nxt[0].date()}（外推）。條件：營收＝最新一期月營收 ≥ 前 24 期最高（公布後 45 個交易日內有效）；技術 5 取 3："
         "c1 近 20 日漲 ≥ 30%｜c2 近 20 根有 ≥ 3 根收漲停｜c3 當日成交額 ≥ 前 20 日均額 × 3｜c4 收盤 ＞ 100 日均線｜c5 收盤 ≥ 近 250 日最高收盤。"
         "同一檔 20 個交易日內只算第一次。表頭可點排序、表格可左右捲；點代號看 K 線圖（虛線 ＝ 明天要到的價格）。</p>"]
    cards = []

    def card(r, zone, lines):
        L = r["_L"]; s = r["代號"]; fr = L["fac"]
        k0 = L["pos"]; i0 = max(0, k0 - 120); sl = slice(i0, k0 + 1)
        df = D.load_stock(s, r["市場"] if r["市場"] in ("twse", "tpex") else "twse", cal).df
        cf = pd.Series(df["close"].to_numpy(float)).ffill().to_numpy()
        ma = {kk: CS.moving_avg(cf, kk)[sl] for kk in (20, 60)}
        hl = [{"px": v * fr, "label": lab, "color": col} for v, lab, col in lines if v is not None and np.isfinite(v)]
        svg = CS.kline_svg([str(z.date()) for z in cal[sl]], df["open"].to_numpy(float)[sl], df["high"].to_numpy(float)[sl], df["low"].to_numpy(float)[sl],
                           df["close"].to_numpy(float)[sl], df["volume"].to_numpy(float)[sl] / 1000.0, ma=ma, marks=[], title=f"{s}", show_title=False, hlines=hl)
        cards.append(f"<details class='card' id='k{zone}{s}'><summary><b>{zone}｜{s} {html.escape(r['名稱'])}</b> 收盤 {r['收盤']:.2f}</summary>"
                     f"<div class='meta'>{conds(L)}<br>營收：{html.escape(str(r.get('最新可用營收期')))} "
                     f"{'成立' if r['營收成立（今天）'] else '未成立'}（距前 24 期高 {P(r.get('距24期高'))}）</div>{svg}</details>")
    # A
    H.append(f"<h2>A 今天已達成（{nxt[0].date()} 開盤可買）：{len(A)} 檔</h2>")
    if len(A):
        H.append("<div class='wrap'><table class='s'><thead><tr><th>排名</th><th class='l'>代號 名稱</th><th>收盤</th><th>relvol</th><th class='l'>條件（✔ 達成）</th><th>營收期</th></tr></thead><tbody>")
        for r in A.to_dict("records"):
            H.append(f"<tr><td data-v='{r['relvol 排名']}'>{r['relvol 排名']}</td><td class='l' data-v='{r['代號']}'><a href='#kA{r['代號']}'>{r['代號']} {html.escape(r['名稱'])}</a></td>"
                     f"<td data-v='{r['收盤']}'>{r['收盤']:.2f}</td><td data-v='{r['relvol']}'>{r['relvol']:.2f}</td><td class='l' data-v='{r['分數']}'>{conds(r['_L'])}</td><td data-v='{r['營收期別']}'>{r['營收期別']}</td></tr>")
            card(r, "A", [])
        H.append("</tbody></table></div>")
    # B
    H.append(f"<h2>B 差一個條件（營收已成立、技術 2 分）：{len(B)} 檔；兩天內可能 {int(B['兩天內可能'].sum()) if len(B) else 0} 檔</h2>")
    if len(B):
        H.append("<p class='note'>「所需漲幅」＝ 明天收盤要漲多少才湊滿 3 分（不靠量：價格條件湊 3；靠量：成交額也達標時價格條件湊 2）。★ ＝ 兩天內可能（所需 ≤ 21%，且近 5 日漲、收盤在 20 日線上）。"
                 "「去重擋住」＝ 20 個交易日內已出過 5 取 3，明天就算湊滿也不會出訊號。</p>")
        H.append("<div class='wrap'><table class='s'><thead><tr><th class='l'>代號 名稱</th><th>收盤</th><th>所需漲幅</th><th>不靠量 收盤≥</th><th>靠量 收盤≥</th><th>c3 成交額≥（億）</th>"
                 "<th>c1 收≥</th><th>c4 收＞</th><th>c5 收≥</th><th class='l'>c2</th><th class='l'>已達成</th><th>★</th><th>去重</th></tr></thead><tbody>")
        for r in B.to_dict("records"):
            L = r["_L"]; star = "★" if r["兩天內可能"] else ""
            H.append(f"<tr class='{'pick' if star else ''}'><td class='l' data-v='{r['代號']}'><a href='#kB{r['代號']}'>{r['代號']} {html.escape(r['名稱'])}</a></td><td data-v='{r['收盤']}'>{r['收盤']:.2f}</td>"
                     f"<td data-v='{r['所需漲幅（排序）']}'>{P(r['所需漲幅（排序）'])}</td><td data-v='{r['不靠量所需收盤']}'>{F2(r['不靠量所需收盤'])}</td><td data-v='{r['靠量所需收盤']}'>{F2(r['靠量所需收盤'])}</td>"
                     f"<td data-v='{r['明天門檻 c3（成交額≥，元）']}'>{r['明天門檻 c3（成交額≥，元）'] / 1e8:.2f}</td><td data-v='{r['明天門檻 c1（收盤≥）']}'>{F2(r['明天門檻 c1（收盤≥）'])}</td>"
                     f"<td data-v='{r['明天門檻 c4（收盤＞）']}'>{F2(r['明天門檻 c4（收盤＞）'])}</td><td data-v='{r['明天門檻 c5（收盤≥）']}'>{F2(r['明天門檻 c5（收盤≥）'])}</td>"
                     f"<td class='l' data-v='{L['s19']}'>{html.escape(r['明天門檻 c2'])}</td><td class='l' data-v='{r['已達成']}'>{conds(L)}</td><td data-v='{1 if star else 0}'>{star}</td>"
                     f"<td data-v='{1 if r['去重擋住'] else 0}'>{'擋住' if r['去重擋住'] else ''}</td></tr>")
            fr = L["fac"]
            card(r, "B", [(L["t1"] / fr, "c1 明天收≥", "#e65100"), (L["t4"] / fr, "c4 明天收＞", "#1565c0"), (L["t5"] / fr, "c5 明天收≥", "#6a1b9a"),
                          (r["不靠量所需收盤"], "不靠量所需", "#c62828")])
        H.append("</tbody></table></div>")
    # C
    H.append(f"<h2>C 技術已 ≥ 3 分、營收還沒成立：{len(C)} 檔</h2>")
    if len(C):
        H.append("<div class='wrap'><table class='s'><thead><tr><th class='l'>代號 名稱</th><th>收盤</th><th>分數</th><th>最新營收期</th><th>距前24期高</th><th>下期需月增</th><th>下次公布期限</th><th class='l'>營收未成立原因</th><th class='l'>技術條件</th></tr></thead><tbody>")
        for r in C.to_dict("records"):
            H.append(f"<tr><td class='l' data-v='{r['代號']}'><a href='#kC{r['代號']}'>{r['代號']} {html.escape(r['名稱'])}</a></td><td data-v='{r['收盤']}'>{r['收盤']:.2f}</td><td data-v='{r['分數']}'>{r['分數']}</td>"
                     f"<td data-v='{r.get('最新可用營收期')}'>{r.get('最新可用營收期')}</td><td data-v='{r.get('距24期高')}'>{P(r.get('距24期高'))}</td><td data-v='{r.get('下期需月增')}'>{P(r.get('下期需月增'))}</td>"
                     f"<td data-v='{r['下次公布法定期限']}'>{r['下次公布法定期限']}</td><td class='l' data-v='{html.escape(r['營收未成立原因'])}'>{html.escape(r['營收未成立原因'])}</td><td class='l' data-v='{r['已達成']}'>{conds(r['_L'])}</td></tr>")
            card(r, "C", [])
        H.append("</tbody></table></div>")
    H.append("<h2>K 線圖</h2>" + CS.legend_html() + "".join(cards))
    H.append(f"<p class='note'>資料：tw-stock-data main {sha[:10]}｜閘：近 20 交易日訊號 ＝ 既有名單 {S['閘（近 20 交易日 AND 訊號 ＝ list_YL13_2026-09-24）']['過']}</p>")
    H.append(JS + "</main></body></html>")
    fn = os.path.join(OUT, f"營量v1_即將達成_{asof}.html")
    open(fn, "w", encoding="utf-8").write("\n".join(H))
    S["網頁"] = os.path.basename(fn); S["網頁 bytes"] = os.path.getsize(fn)


if __name__ == "__main__":
    main()

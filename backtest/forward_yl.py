# -*- coding: utf-8 -*-
"""照規則簿：營量 v1／營飆 v1 前瞻「照規則」欄（裁定 seq273 起點 2026-09-29、三檔算入；seq341 實際欄停記、照規則欄照舊）——回測線，2026-10-14。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.forward_yl [--procs 2]          # 補到最新資料日（自己算訊號）
    ~/tw-p16/.venv/bin/python -m backtest.forward_yl --month 202610 [--out 檔]                                 # 月底彙整三列
    每日名單（backtest/daily_list.py）每次產檔都會呼叫 update()（用名單同一次算好的訊號，⛔ 不另算）

⭐ 待裁定核（本簿自己定的讀法，寫死；裁定改了就另開版本、舊紀錄照留）：
  ① 營飆抽籤 ＝ 回測引擎 research11.simulate_mtm 的 pick=None（rng.permutation），種子 ＝ 營飆 v1 r0 的種子
     rerun17.P10_SEED0 ＋ 0 ＝ default_rng(1000)，從起點那天開始抽（前瞻是新的一條 rng，⛔ 不接回測那條）；
     當天候選依【代號】由小到大排好再 permutation（引擎對候選列序抽）。⚠ 營飆 v1 沒有排名鍵 ⇒ 用不到 pick_tie。
  ② 營量挑法 ＝ 引擎 pick="relvol"（relvol 大者先，同分照代號序）；relvol ＝ 訊號日成交額 ÷ 前 60 根有效 K 棒成交額中位數（與名單同式）
  ③ 停止交易／缺口：持有期間連續 5 個交易日沒有有效 K 棒（research11 缺口 ≥5 即壞根，裁定 seq335）⇒ 第 6 個交易日開盤前
     以最後一根有效收盤強制出場（引擎 stop_force，鍵 ＝ 第 5 個缺日；⛔ 不回頭改第 1 個缺日，沒有前視）
  ④ 進場日（訊號隔一個交易日）沒有有效 K 棒或開盤無效 ⇒ 該名額當天持現金、⛔ 不遞補、⛔ 不順延（引擎 tradable 的 halt_in；
     漲停、跌停一律不擋 ＝ 營量／營飆 v1 原件）
  ⑤ 大盤閘（營飆）＝ 訊號日（＝ 進場前一個交易日 t−1）0050 還原收盤 ＞ 200 日均（與每日名單第一節同一個 reg[t−1]，裁定 seq183）
其餘全照引擎：出場 ＝ 進場那根算第 1 根的第 60／120 根有效 K 棒收盤；每槽 ＝ 前一日權益 ÷ 槽數、現金不夠用剩下的；
同檔不重複持有；成本來回 0.585% 出場時扣；現金報酬 0；同一天 排程出場 → 新部位（引擎慣例：出場日當天開盤那個槽就能再進）。

訊號 ＝ 每日名單第一、二節同一個 A 名單來源（list_yl13_watch.compute 的 AND；資料日當天用名單的 A）；起點 ＝ 2026-09-29 進場（訊號日 2026-09-24）。
紀錄（backtest/forward/yl_rule/，只追加；環境變數 FY_BOOK_DIR 可改到別處，測試用）：
  signals.csv    每筆訊號（訊號日、代號、名稱、relvol、營飆大盤閘、main、寫入時間）；⭐ 資料日 ＜ 本次資料日的訊號凍結，重放一律讀這份
  positions.csv  每筆進場（策略、代號、名稱、訊號日、進場日、進場價、出場日、出場價、狀態、預定出場日、報酬%、金額佔權益、備註）
                 ⭐ 已出場列凍結（重放結果若不同只記 runlog）；價格欄 ＝ 未還原（實際成交價）；報酬% ＝ 還原價、已出場扣成本
  equity.csv     逐日（策略、權益、現金、持倉數、0050 還原收盤、0050 還原（起點前一日 ＝ 1））；⭐ 日期 ＜ 本次資料日的列凍結
  draws.csv      每個進場日每個策略：空槽、候選、買進、落選（槽滿／抽籤／relvol 排名）、已持有、停牌未買
  state.json     本次資料日、main、明天空槽、明天到期、明天照規則買／落選（預測：以明天各檔都有成交推算）
  runlog.md      每次執行一段（重放與凍結紀錄的差、訊號重算差、警示）
同資料日重跑（main 換新 sha、資料日不變）⇒ 該資料日的列以新資料重寫；有更新的資料日之後就凍結。⛔ 資料日倒退 ⇒ 不寫、只回報。
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
from datetime import datetime
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

from . import data as D
from . import research11 as R
from . import gate_b_status as GB

HERE = os.path.dirname(os.path.abspath(__file__))
BOOK_DEFAULT = os.path.join(HERE, "forward", "yl_rule")
START = "2026-09-29"                                     # 第一個進場日（裁定 seq273）
SEED_YF_R0 = 1000                                        # rerun17.P10_SEED0 ＋ r0
SEED_YL = 7000                                           # rerun17.P1_SEED0 ＋ 0（pick=relvol ⇒ 引擎不抽 rng，只是形式上傳）
GAP_FORCE = 5                                            # 連續缺 5 個交易日 ⇒ 第 6 天強制出場
STRATS = {"營量v1": {"H": 60, "N": 20, "pick": "relvol", "gate": False, "seed": SEED_YL, "short": "營量"},
          "營飆v1": {"H": 120, "N": 10, "pick": None, "gate": True, "seed": SEED_YF_R0, "short": "營飆"}}
DRAW_NOTE = "營飆抽籤 ＝ 引擎 pick=None、default_rng(1000)（營飆 v1 r0 的種子）自起點起抽、候選依代號排序（待裁定核）"
BIG = 10 ** 7


def book_dir():
    return os.environ.get("FY_BOOK_DIR") or BOOK_DEFAULT


def _now():
    return datetime.now(ZoneInfo("Asia/Taipei")).strftime("%Y-%m-%d %H:%M:%S")


def _read(p, allstr=False):
    if not os.path.exists(p) or os.path.getsize(p) == 0:
        return None
    return pd.read_csv(p, dtype=(str if allstr else {"代號": str}), encoding="utf-8-sig", keep_default_na=not allstr)


def _write(df, p):
    tmp = p + ".tmp"
    df.to_csv(tmp, index=False, encoding="utf-8-sig", float_format="%.12g")
    os.replace(tmp, p)


def _bars(sid, mk, cal):
    B = R.load_bars(sid, mk, cal)
    if B is None:
        return None
    raw = pd.read_csv(os.path.join(D.DATA, "stocks", f"{sid}.csv"), dtype={"date": str}, usecols=["date", "open", "close"])
    raw["date"] = pd.to_datetime(raw["date"]); raw = raw.drop_duplicates("date").set_index("date")
    B["raw_open"] = pd.to_numeric(raw["open"].reindex(cal), errors="coerce").to_numpy(float)
    B["raw_close"] = pd.to_numeric(raw["close"].reindex(cal), errors="coerce").to_numpy(float)
    df = B["df"]
    B["adj_close"] = df["close"].to_numpy(float)
    B["adj_open"] = df["open"].to_numpy(float)
    return B


def _relvol(B, k):
    amt = B["amt"]
    med = float(np.nanmedian(amt[max(k - 60, 0):k])) if k >= 1 else np.nan
    return float(amt[k]) / med if med > 0 and np.isfinite(amt[k]) else np.nan


# ═════════════ 訊號 ═════════════
def _collect_signals(cal, AND, names, mkt, A_today, frozen, frozen_upto, reg, sha, log):
    """回 (S, 重算差異訊息)。frozen_upto ＝ 凍結到哪個日曆位置（含）；之後到資料日的訊號重算。"""
    n = len(cal); p_start = int(cal.searchsorted(pd.Timestamp(START))); p0 = p_start - 1
    msgs = []
    rows = []
    if frozen is not None and len(frozen):
        fpos = frozen["訊號日"].map(lambda d: int(cal.get_loc(pd.Timestamp(d))))
        keep = frozen[fpos <= frozen_upto]
        rows += keep.to_dict("records")
        # 重算差（描述，⛔ 不改凍結）
        for p in range(p0, frozen_upto + 1):
            a = set(AND.loc[AND["pos"] == p, "sid"].astype(str)); b = set(keep.loc[fpos[fpos <= frozen_upto] == p, "代號"].astype(str))
            if a != b:
                msgs.append(f"訊號日 {cal[p].date()}：凍結 {sorted(b)}｜重算 {sorted(a)}（只在凍結 {sorted(b - a)}、只在重算 {sorted(a - b)}；照凍結）")
    lo = max(p0, frozen_upto + 1)
    now = _now()
    for p in range(lo, n):
        if p == n - 1 and A_today is not None:
            sids = sorted(str(s) for s in A_today)
            a = set(AND.loc[AND["pos"] == p, "sid"].astype(str))
            if a != set(sids):
                msgs.append(f"資料日 {cal[p].date()}：名單 A {sids}｜AND {sorted(a)}（照名單 A）")
        else:
            sids = sorted(set(AND.loc[AND["pos"] == p, "sid"].astype(str)))
        for s in sids:
            rows.append({"訊號日": str(cal[p].date()), "代號": s, "名稱": names.get(s, ""), "relvol": np.nan,
                         "營飆大盤閘": bool(reg[p]), "main": sha[:10], "寫入時間": now})
    S = pd.DataFrame(rows, columns=["訊號日", "代號", "名稱", "relvol", "營飆大盤閘", "main", "寫入時間"])
    S["代號"] = S["代號"].astype(str)
    S["營飆大盤閘"] = [v if isinstance(v, (bool, np.bool_)) else str(v).strip() == "True" for v in S["營飆大盤閘"]]
    S["relvol"] = pd.to_numeric(S["relvol"], errors="coerce")
    S = S.sort_values(["訊號日", "代號"], kind="stable").reset_index(drop=True)
    return S, msgs


# ═════════════ 引擎 ═════════════
def _engine_inputs(S, bars, cal):
    """closes／opens／tradable：長度 n＋1（最後一天 ＝ 明天，合成：開盤 ＝ 收盤 ＝ 資料日收盤、視為有成交）。"""
    n = len(cal)
    closes, opens, trd = {}, {}, {}
    for sid in sorted(set(S["代號"])):
        B = bars[sid]
        c = pd.Series(B["adj_close"]).ffill().to_numpy(float)
        o = B["adj_open"].copy()
        valid = np.isfinite(B["adj_close"])
        ok = valid & np.isfinite(o) & (o > 0)
        last = c[-1]
        closes[sid] = np.append(c, last); opens[sid] = np.append(o, last)
        z = np.zeros(n + 1, bool)
        trd[sid] = {"trd": np.append(ok, True), "up_o": z, "dn_o": z, "dn_c": z}
    return closes, opens, trd


def _force_days(S, bars, cal):
    """{sid: q}：最早進場日之後第一次連續缺 GAP_FORCE 個交易日的第 GAP_FORCE 個缺日 q（⇒ 引擎在 q＋1 以 q 的 ffill 收盤 ＝ 最後有效收盤出場）。"""
    n = len(cal); out = {}
    for sid, g in S.groupby("代號"):
        e0 = min(int(cal.get_loc(pd.Timestamp(d))) + 1 for d in g["訊號日"])
        valid = np.isfinite(bars[sid]["adj_close"])
        run = 0
        for p in range(e0 + 1, n):
            run = 0 if valid[p] else run + 1
            if run == GAP_FORCE:
                out[sid] = p; break
    return out


def _sig_for(name, S, bars, cal, opens, closes):
    sp = STRATS[name]; H = sp["H"]; n = len(cal)
    rows = []
    for r in S.itertuples():
        if sp["gate"] and not bool(r.營飆大盤閘):
            continue
        p = int(cal.get_loc(pd.Timestamp(r.訊號日))); e = p + 1; B = bars[r.代號]
        idx = B["idx"]; k = int(np.searchsorted(idx, p))
        if k >= len(idx) or idx[k] != p:
            raise SystemExit(f"⛔ {r.代號} 訊號日 {r.訊號日} 不是有效 K 棒")
        idx_x = np.append(idx, n)                                     # 明天（合成日）視為有成交
        ep = opens[r.代號][e]
        if k + H < len(idx_x):
            xb = int(idx_x[k + H])
            g = float(closes[r.代號][xb]) / ep - 1 if np.isfinite(ep) and ep > 0 else 0.0     # xb ＝ n（明天）⇒ 合成價，只為讓引擎在明天騰槽
        else:
            xb, g = BIG, 0.0
        rows.append({"sid": r.代號, "entry_pos": e, f"xpos_H{H}": xb, f"g_H{H}": g, "relvol": float(r.relvol), "signal_pos": p})
    return pd.DataFrame(rows, columns=["sid", "entry_pos", f"xpos_H{H}", f"g_H{H}", "relvol", "signal_pos"])


def _run(name, sig, closes, opens, trd, sf, n):
    sp = STRATS[name]; lg, au = [], []
    out = R.simulate_mtm(sig, f"H{sp['H']}", sp["N"], np.random.default_rng(sp["seed"]), closes, opens, n + 1,
                         return_equity=True, pick=sp["pick"], log=lg, audit=au, tradable=trd, stop_force=sf)
    return out, lg, au


def _positions(name, sig, au, sf, cal):
    """audit ⇒ 每筆部位：t_in、t_out（None ＝ 還在）、ep、px_out、amt、eq_prev、xpos、forced。"""
    H = STRATS[name]["H"]; n = len(cal)
    xmap = {(r.sid, int(r.entry_pos)): int(getattr(r, f"xpos_H{H}")) for r in sig.itertuples()}
    P, op = [], {}
    for a in au:
        if a["side"] == "buy":
            rec = {"sid": a["sid"], "t_in": int(a["t"]), "ep": float(a["px"]), "amt": float(a["amt"]), "eq_prev": float(a["equity_prev"]),
                   "t_out": None, "px_out": np.nan, "forced": False}
            rec["xpos"] = xmap[(a["sid"], rec["t_in"])]
            P.append(rec); op.setdefault(a["sid"], []).append(rec)
        else:
            rec = op[a["sid"]].pop(0)
            rec["t_out"] = int(a["t"]); rec["px_out"] = float(a["px"])
            rec["forced"] = bool(a["sid"] in sf and rec["t_out"] == sf[a["sid"]] + 1 and rec["t_out"] < rec["xpos"])
    return P


def _held_at(P, t):
    """第 t 天收盤後仍持有的部位（引擎：t_out ＝ t 那筆在 t 開盤前就結清）。"""
    return [p for p in P if p["t_in"] <= t and (p["t_out"] is None or p["t_out"] > t)]


def _draws(name, sig, lg, P, cal):
    """每個進場日：空槽、候選、買進、落選、已持有、停牌。t ＝ n 是明天（預測）。"""
    N = STRATS[name]["N"]; n = len(cal)
    why = {(int(r["t"]), str(r["sid"])): r["reason"] for r in lg}
    out = []
    for t, g in sig.groupby("entry_pos"):
        t = int(t)
        if t < int(cal.searchsorted(pd.Timestamp(START))):
            continue
        open_before = [p for p in P if p["t_in"] < t and (p["t_out"] is None or p["t_out"] > t)]
        free = N - len(open_before)
        held_s = {p["sid"] for p in open_before}
        rec = {"buy": [], "lose": [], "held": [], "halt": []}
        for s in g["sid"]:
            w = why.get((t, s))
            if w == "in":
                rec["buy"].append(s)
            elif w in ("halt_in", "limit_up"):
                rec["halt"].append(s)
            elif w == "c" or s in held_s:
                rec["held"].append(s)
            else:
                rec["lose"].append(s)                                      # a（槽滿／抽籤落選／排名落選）或沒進引擎那段（槽 0）
        dt = str(cal[t].date()) if t < n else "明天"
        out.append({"t": t, "進場日": dt, "策略": name, "空槽": int(free), "候選": "、".join(g["sid"]),
                    "買進": "、".join(rec["buy"]), "落選": "、".join(rec["lose"]), "已持有": "、".join(rec["held"]), "停牌未買": "、".join(rec["halt"]),
                    "落選原因": ("" if not rec["lose"] else ("槽滿（空槽 0）" if free <= 0 else
                                                       ("抽籤落選" if STRATS[name]["pick"] is None else "relvol 排名落選"))), "_rec": rec})
    return out


# ═════════════ 主流程 ═════════════
def update(cal, AND, stocks, sha, DATA, log=print, A_today=None, write=True):
    """補到資料日（cal 最後一天）。回 info（給每日名單）。A_today ＝ 名單第一、二節當天 A 的代號（None ⇒ 用 AND）。"""
    D.DATA = DATA
    from . import list_prereg10 as LP
    D.DATA = DATA                                              # list_prereg10 import 時會把 D.DATA 指到快照 ⇒ 再指回來
    bk = book_dir(); os.makedirs(bk, exist_ok=True)
    n = len(cal); asof = str(cal[-1].date())
    p_start = int(cal.searchsorted(pd.Timestamp(START)))
    st_old = json.load(open(os.path.join(bk, "state.json"), encoding="utf-8")) if os.path.exists(os.path.join(bk, "state.json")) else None
    if st_old and st_old["資料日"] > asof:
        raise RuntimeError(f"資料日倒退：簿已記到 {st_old['資料日']}，本次 {asof} ⇒ 不寫")
    frozen = _read(os.path.join(bk, "signals.csv"))
    if st_old and frozen is not None:
        fu = int(cal.get_loc(pd.Timestamp(st_old["資料日"])))
        frozen_upto = fu if st_old["資料日"] < asof else n - 2
    else:
        frozen_upto = p_start - 2
    names = stocks.drop_duplicates("stock_id").set_index("stock_id")["name"].astype(str).to_dict()
    mkt = stocks.drop_duplicates("stock_id").set_index("stock_id")["market"].astype(str).to_dict()
    bench, ma, reg = LP.regime_arrays(cal)
    S, sig_msgs = _collect_signals(cal, AND, names, mkt, A_today, frozen, frozen_upto, reg, sha, log)
    bars = {}
    warn = []
    for sid in sorted(set(S["代號"])):
        B = _bars(sid, mkt.get(sid, "twse"), cal)
        if B is None:
            raise SystemExit(f"⛔ {sid} 讀不到有效 K 棒")
        bars[sid] = B
    for i, r in S.iterrows():                                   # 新訊號補 relvol（凍結的照舊）
        if not np.isfinite(float(r["relvol"])):
            p = int(cal.get_loc(pd.Timestamp(r["訊號日"]))); k = int(np.searchsorted(bars[r["代號"]]["idx"], p))
            S.at[i, "relvol"] = _relvol(bars[r["代號"]], k)
    closes, opens, trd = _engine_inputs(S, bars, cal)
    sf = _force_days(S, bars, cal)
    # 壞根（非缺口）在持有窗內 ⇒ 只警示
    for sid, B in bars.items():
        nb = B["next_bad"]; idx = B["idx"]
        e0 = min(int(cal.get_loc(pd.Timestamp(d))) + 1 for d in S.loc[S["代號"] == sid, "訊號日"])
        ks = np.flatnonzero(idx >= e0)
        if len(ks) and nb[ks[0]] < len(idx):
            kb = nb[ks[0]]; gap = idx[kb] - idx[kb - 1] - 1 if kb > 0 else 0
            if gap < GAP_FORCE:
                warn.append(f"{sid}：進場後 {cal[idx[kb]].date()} 是壞根（非缺口：斷點或幽靈事件）⇒ 價格可能不連續，請人工核")
    res = {}
    for name in STRATS:
        sig = _sig_for(name, S, bars, cal, opens, closes)
        if not len(sig):                                       # 一筆訊號都沒有（例：大盤閘一直關）⇒ 空手
            res[name] = {"sig": sig, "out": {"equity": np.ones(n + 1), "hold_val": np.zeros(n + 1)}, "lg": [], "P": [], "draws": []}
            continue
        out, lg, au = _run(name, sig, closes, opens, trd, sf, n)
        P = _positions(name, sig, au, sf, cal)
        res[name] = {"sig": sig, "out": out, "lg": lg, "P": P, "draws": _draws(name, sig, lg, P, cal)}
    fut, basis = GB.future_trading_days(cal, 2 * 120 + 10, fixed_holidays_uncovered=True)
    nxt = str(fut[0].date())
    base0050 = float(bench[p_start - 1])

    def fdate(t):
        return str(cal[t].date()) if t < n else str(fut[t - n].date())

    def planned_exit(name, p):
        H = STRATS[name]["H"]
        if p["xpos"] < n:
            return fdate(p["xpos"])
        if p["xpos"] == n:
            return nxt
        held = int(np.isfinite(bars[p["sid"]]["adj_close"][p["t_in"]:n]).sum())
        rem = H - held
        return str(fut[rem - 1].date()) + "（外推）"
    # ── positions
    prow = []
    for name, X in res.items():
        for p in X["P"]:
            if p["t_in"] >= n:
                continue
            B = bars[p["sid"]]; t_in = p["t_in"]
            row = {"策略": name, "代號": p["sid"], "名稱": names.get(p["sid"], ""), "訊號日": str(cal[t_in - 1].date()), "進場日": str(cal[t_in].date()),
                   "進場價": B["raw_open"][t_in], "出場日": "", "出場價": np.nan, "狀態": "持有中", "預定出場日": planned_exit(name, p),
                   "報酬%": np.nan, "金額佔權益": p["amt"] / p["eq_prev"] if p["eq_prev"] > 0 else np.nan, "備註": ""}
            if p["t_out"] is not None and p["t_out"] < n:
                t_o = p["t_out"]; g = p["px_out"] / p["ep"] - 1
                row.update({"出場日": str(cal[t_o].date()), "報酬%": round((g - R.COST) * 100, 4)})
                if p["forced"]:
                    L = int(np.flatnonzero(np.isfinite(B["adj_close"][:t_o]))[-1])
                    row.update({"出場價": B["raw_close"][L], "狀態": "強制出場",
                                "備註": f"連 {GAP_FORCE} 個交易日無成交 ⇒ 以最後成交日 {cal[L].date()} 收盤價出場；報酬已扣成本"})
                else:
                    row.update({"出場價": B["raw_close"][t_o], "狀態": "已出場", "備註": "報酬已扣成本（還原價）"})
            else:
                cur = B["adj_close"][:n]; cl = float(pd.Series(cur).ffill().iloc[-1])
                row["報酬%"] = round((cl / p["ep"] - 1) * 100, 4)
                row["備註"] = "持有中報酬未扣成本（還原價）"
                if p["t_out"] == n:
                    row["備註"] += "；" + ("明天強制出場（連 5 個交易日無成交）" if p["forced"] else f"明天 {nxt} 收盤到期")
            prow.append(row)
    PC = ["策略", "代號", "名稱", "訊號日", "進場日", "進場價", "出場日", "出場價", "狀態", "預定出場日", "報酬%", "金額佔權益", "備註"]
    Pnew = pd.DataFrame(prow, columns=PC)
    Pold = _read(os.path.join(bk, "positions.csv"))
    pos_msgs = []
    if Pold is not None and len(Pold):
        fz = Pold[Pold["狀態"].isin(["已出場", "強制出場"]) & (Pold["出場日"].astype(str) < asof)]
        key = lambda d: list(zip(d["策略"], d["代號"].astype(str), d["進場日"].astype(str)))
        fk = set(key(fz))
        for k_, r_ in zip(key(Pnew), Pnew.to_dict("records")):
            if k_ in fk:
                o_ = fz[(fz["策略"] == k_[0]) & (fz["代號"] == k_[1]) & (fz["進場日"] == k_[2])].iloc[0]
                if str(o_["出場日"]) != r_["出場日"]:
                    pos_msgs.append(f"{k_}：凍結出場日 {o_['出場日']}｜重放 {r_['出場日']}（照凍結）")
        miss = fk - set(key(Pnew))
        for m in sorted(miss):
            pos_msgs.append(f"{m}：凍結已出場、重放沒有這筆（照凍結保留）")
        Pnew = pd.concat([fz, Pnew[[k_ not in fk for k_ in key(Pnew)]]], ignore_index=True)
        old_open = set(key(Pold[~Pold.index.isin(fz.index)]))
        for m in sorted(old_open - set(key(Pnew))):
            pos_msgs.append(f"{m}：上次記為持有中、這次重放沒有這筆 ⇒ 請查（訊號凍結下不該發生）")
    Pnew = Pnew.sort_values(["策略", "進場日", "代號"], kind="stable").reset_index(drop=True)
    # ── equity
    erow = []
    for name, X in res.items():
        eq = np.asarray(X["out"]["equity"], float); hv = np.asarray(X["out"]["hold_val"], float)
        for t in range(p_start, n):
            erow.append({"日期": str(cal[t].date()), "策略": name, "權益": eq[t], "現金": eq[t] - hv[t], "持倉數": len(_held_at(X["P"], t)),
                         "0050還原收盤": float(bench[t]), "0050還原（起點前一日=1）": float(bench[t]) / base0050, "main": sha[:10]})
    Enew = pd.DataFrame(erow, columns=["日期", "策略", "權益", "現金", "持倉數", "0050還原收盤", "0050還原（起點前一日=1）", "main"])
    Eold = _read(os.path.join(bk, "equity.csv"))
    eq_msgs = []
    if Eold is not None and len(Eold):
        fz = Eold[Eold["日期"].astype(str) < asof]
        m = fz.merge(Enew, on=["日期", "策略"], suffixes=("_舊", "_新"))
        if len(m):
            d1 = float(np.max(np.abs(m["權益_舊"] - m["權益_新"]))); d2 = float(np.max(np.abs(m["0050還原（起點前一日=1）_舊"] - m["0050還原（起點前一日=1）_新"])))
            eq_msgs.append(f"凍結列 {len(m)} 列：權益重放差最大 {d1:.2e}、0050 指數差最大 {d2:.2e}（照凍結）")
        Enew = pd.concat([fz, Enew[Enew["日期"].astype(str) >= asof]], ignore_index=True)
    Enew = Enew.sort_values(["策略", "日期"], kind="stable").reset_index(drop=True)
    # ── draws
    drow = []
    for name, X in res.items():
        for d in X["draws"]:
            if d["t"] < n:
                drow.append({k: v for k, v in d.items() if k not in ("t", "_rec")})
    Dnew = pd.DataFrame(drow, columns=["進場日", "策略", "空槽", "候選", "買進", "落選", "已持有", "停牌未買", "落選原因"])
    Dold = _read(os.path.join(bk, "draws.csv"), allstr=True)
    if Dold is not None and len(Dold):
        fz = Dold[Dold["進場日"].astype(str) < asof]
        Dnew = pd.concat([fz, Dnew[Dnew["進場日"].astype(str) >= asof]], ignore_index=True)
    Dnew = Dnew.sort_values(["進場日", "策略"], kind="stable").reset_index(drop=True)
    # ── info（明天）
    info = {"資料日": asof, "main": sha[:10], "明天": nxt, "大盤閘": bool(reg[n - 1]), "策略": {}, "抽法": DRAW_NOTE}
    for name, X in res.items():
        sp = STRATS[name]; P = X["P"]
        held = _held_at(P, n - 1)
        due = [p["sid"] for p in held if p["t_out"] == n and not p["forced"]]
        frc = [p["sid"] for p in held if p["t_out"] == n and p["forced"]]
        tm = [d for d in X["draws"] if d["t"] == n]
        free = sp["N"] - (len(held) - len(due) - len(frc))
        rec = tm[0]["_rec"] if tm else {"buy": [], "lose": [], "held": [], "halt": []}
        info["策略"][name] = {"N": sp["N"], "持有": [p["sid"] for p in held], "持有檔數": len(held), "明天空槽": int(free),
                             "明天到期": due, "明天強制出場": frc, "明天照規則買": rec["buy"], "明天落選": rec["lose"],
                             "已持有": {p["sid"]: str(cal[p["t_in"]].date()) for p in held if p["sid"] in rec["held"]},
                             "relvol 排名": ({s: i + 1 for i, s in enumerate(X["sig"][X["sig"]["entry_pos"] == n].sort_values("relvol", ascending=False, kind="stable")["sid"])}
                                            if sp["pick"] == "relvol" else {})}
    if write:
        for df, fn in ((S, "signals.csv"), (Pnew, "positions.csv"), (Enew, "equity.csv"), (Dnew, "draws.csv")):
            _write(df, os.path.join(bk, fn))
        st = dict(info); st.update({"起點": START, "寫入時間": _now(), "說明": "每日名單／forward_yl.update 自動寫；只追加、已出場凍結"})
        json.dump(st, open(os.path.join(bk, "state.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        L = [f"## {_now()}（台北）資料日 {asof}｜main {sha[:10]}", ""]
        for name, v in info["策略"].items():
            last_d = [d for d in res[name]["draws"] if d["t"] == n - 1]
            ld = last_d[0] if last_d else None
            L.append(f"- {name}：持有 {v['持有檔數']}／{v['N']}（{'、'.join(v['持有'])}）｜今天進場 {ld['買進'] if ld and ld['買進'] else '無'}"
                     f"{('｜今天落選 ' + ld['落選'] + '（' + ld['落選原因'] + '）') if ld and ld['落選'] else ''}"
                     f"｜明天空槽 {v['明天空槽']}（到期 {v['明天到期'] or '無'}、強制 {v['明天強制出場'] or '無'}）｜明天照規則買 {v['明天照規則買'] or '無'}"
                     f"｜明天落選 {v['明天落選'] or '無'}｜權益 {float(res[name]['out']['equity'][n - 1]):.6f}")
        L.append(f"- 0050 還原（起點前一日=1）：{float(bench[n - 1]) / base0050:.6f}｜大盤閘（{asof}）{'開' if info['大盤閘'] else '關'}")
        for msg in sig_msgs + pos_msgs + eq_msgs + warn:
            L.append(f"- ⚠ {msg}" if not msg.startswith("凍結列") else f"- {msg}")
        L.append("")
        rl = os.path.join(bk, "runlog.md")
        head = "" if os.path.exists(rl) else "# 照規則簿 runlog（backtest/forward_yl.py；只追加）\n\n" + DRAW_NOTE + "\n\n"
        with open(rl, "a", encoding="utf-8") as f:
            f.write(head + "\n".join(L) + "\n")
    log(f"[照規則簿] 資料日 {asof}｜" + "｜".join(f"{k} {v['持有檔數']}/{v['N']} 明天空槽 {v['明天空槽']}" for k, v in info["策略"].items())
        + (f"｜⚠ {len(sig_msgs + pos_msgs + warn)} 則差異／警示" if (sig_msgs or pos_msgs or warn) else ""))
    info["_res"] = res; info["_msgs"] = sig_msgs + pos_msgs + eq_msgs + warn
    return info


# ═════════════ 每日名單用 ═════════════
def daily_tags(info, sec1_codes, sec2_codes, gate_on):
    """回 (第一節節首行, 第二節節首行, {代號: 第一節標記}, {代號: 第二節標記})。"""
    yf, yl = info["策略"]["營飆v1"], info["策略"]["營量v1"]

    def head(v, nm):
        due = v["明天到期"] + v["明天強制出場"]
        return f"照規則簿：{nm}目前 {v['持有檔數']}／{v['N']} 檔、明天空槽 {v['明天空槽']}" + (f"（含明天收盤到期 {len(due)} 檔：{'、'.join(due)}）" if due else "")
    h1 = head(yf, "營飆") + ("" if gate_on else "；大盤閘關，明天照規則不進") + "。"
    h2 = head(yl, "營量") + "。"
    yl_buy = set(yl["明天照規則買"]); yf_buy = set(yf["明天照規則買"])

    def yl_txt(s):
        if s in yl_buy:
            return None
        if s in yl["已持有"]:
            return f"營量照規則簿已持有（{yl['已持有'][s]} 進），不重複買"
        k = yl["明天空槽"]
        return f"營量已滿（空槽 {k}{'' if k <= 0 else '、relvol 第 ' + str(yl['relvol 排名'].get(s, '?')) + ' 名落選'}）"
    t1, t2 = {}, {}
    for s in sec1_codes:
        if s in yf_buy:
            t1[s] = "照規則買" + ("" if yl_txt(s) is None else f"（{yl_txt(s)}⇒ 這檔只買營飆那份）")
        elif s in yf["已持有"]:
            t1[s] = f"營飆照規則簿已持有（{yf['已持有'][s]} 進），不重複買" + ("" if yl_txt(s) is None else f"；{yl_txt(s)}")
        else:
            k = yf["明天空槽"]
            a = f"營飆已滿（空槽 {k}{'' if k <= 0 else '、抽籤落選'}）"
            t1[s] = a + ("⇒ 這檔只買營量那份" if s in yl_buy else f"；營量也已滿，照規則不買" if not s in yl["已持有"] else f"；{yl_txt(s)}")
    for s in sec2_codes:
        x = yl_txt(s)
        t2[s] = "照規則買" if x is None else x + ("⇒ 這檔只買營飆那份" if (gate_on and s in yf_buy) else "⇒ 照規則不買營量那份")
    return h1, h2, t1, t2


# ═════════════ 月底彙整 ═════════════
def month_summary(yyyymm, book=None, cal=None):
    """前瞻彙整三列（營量v1照規則、營飆v1照規則、0050還原）。欄：項目, 期別, 當月報酬%, 累計報酬%（起點）, 起點日, 筆數或持股數, 備註。"""
    bk = book or book_dir()
    E = _read(os.path.join(bk, "equity.csv")); P = _read(os.path.join(bk, "positions.csv"))
    st = json.load(open(os.path.join(bk, "state.json"), encoding="utf-8"))
    ym = f"{str(yyyymm)[:4]}-{str(yyyymm)[4:6]}"
    if cal is None:
        try:
            D.DATA = os.path.expanduser(f"~/h2data/{_full_sha(st['main'])}/data"); cal = D.load_calendar()
        except Exception:
            cal = None
    month_last = None
    if cal is not None:
        dm = [d for d in cal if d.strftime("%Y-%m") == ym]
        if dm and any(d.strftime("%Y-%m") > ym for d in cal):
            month_last = str(dm[-1].date())
        elif cal[-1].strftime("%Y-%m") <= ym:
            fut, _ = GB.future_trading_days(cal, 40, fixed_holidays_uncovered=True)
            fm = [d for d in fut if d.strftime("%Y-%m") == ym]
            month_last = str(fm[-1].date()) if fm else (str(dm[-1].date()) if dm else None)
    rows = []
    for name, item in (("營量v1", "營量v1照規則"), ("營飆v1", "營飆v1照規則"), (None, "0050還原")):
        e = E[E["策略"] == (name or "營量v1")].sort_values("日期")
        col = "權益" if name else "0050還原（起點前一日=1）"
        cur = e[e["日期"].str[:7] == ym]; prev = e[e["日期"].str[:7] < ym]
        if not len(cur):
            rows.append({"項目": item, "期別": str(yyyymm), "當月報酬%": np.nan, "累計報酬%（起點）": np.nan, "起點日": START,
                         "筆數或持股數": "", "備註": "本月沒有資料"}); continue
        v1 = float(cur[col].iloc[-1]); v0 = float(prev[col].iloc[-1]) if len(prev) else 1.0
        end_d = str(cur["日期"].iloc[-1])
        done = month_last is not None and end_d >= month_last
        note = f"資料至 {end_d}" + ("" if done else f"（月未結束{'，月底 ' + month_last if month_last else ''}）")
        if name:
            p = P[P["策略"] == name]
            nin = int((p["進場日"].astype(str).str[:7] == ym).sum()); nout = int((p["出場日"].fillna("").astype(str).str[:7] == ym).sum())
            cnt = f"月底持股 {int(cur['持倉數'].iloc[-1])} 檔；當月進場 {nin} 筆、出場 {nout} 筆"
            note += "；照規則簿 backtest/forward/yl_rule（引擎 research11.simulate_mtm）；成本 0.585% 出場扣、持有中未扣"
            if name == "營飆v1":
                note += "；" + DRAW_NOTE + "；⚠ 彙整格式原寫「中位顆」，本簿只一顆 r0"
        else:
            cnt = "—"
            note += "；0050 還原收盤（含息）買進持有，起點前一交易日收盤 ＝ 1"
        rows.append({"項目": item, "期別": str(yyyymm), "當月報酬%": round((v1 / v0 - 1) * 100, 4), "累計報酬%（起點）": round((v1 - 1) * 100, 4),
                     "起點日": START, "筆數或持股數": cnt, "備註": note})
    return pd.DataFrame(rows, columns=["項目", "期別", "當月報酬%", "累計報酬%（起點）", "起點日", "筆數或持股數", "備註"])


def _full_sha(short):
    import subprocess
    r = subprocess.run(["git", "-C", os.path.dirname(HERE), "rev-parse", short], capture_output=True, text=True)
    return r.stdout.strip() or short


def sync_to(dst):
    """把簿複製到 dst（檢查用；正式同步到信箱由回測主 session 做）。"""
    os.makedirs(dst, exist_ok=True)
    for f in os.listdir(book_dir()):
        shutil.copy2(os.path.join(book_dir(), f), os.path.join(dst, f))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--procs", type=int, default=2)
    ap.add_argument("--month", help="YYYYMM ⇒ 只產月底彙整三列")
    ap.add_argument("--out", help="--month 的輸出檔（預設印出）")
    ap.add_argument("--sync", help="跑完把簿複製到這個資料夾（檢查用）")
    a = ap.parse_args()
    if a.month:
        df = month_summary(a.month)
        if a.out:
            os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
            df.to_csv(a.out, index=False, encoding="utf-8-sig")
        print(df.to_string(index=False))
        return
    from . import list_yl13_watch as W
    X = W.compute(a.procs, print)
    DATA = os.path.expanduser(f"~/h2data/{X['sha']}/data")
    A = X["A"]
    update(X["cal"], X["AND"], X["stocks"], X["sha"], DATA, print, A_today=(list(A["代號"]) if len(A) else []))
    if a.sync:
        sync_to(a.sync)


if __name__ == "__main__":
    main()

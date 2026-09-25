# -*- coding: utf-8 -*-
"""selftest_gate_b_status：門檻B 逐檔判定工具（backtest/gate_b_status.py）的硬性查核——⛔ 全部要過。

    ~/tw-p16/.venv/bin/python -m backtest.selftest_gate_b_status

 A 回歸：隨機抽 30 個（股, 量測日）（2026-03 以前；分層：訊號 10／合格非訊號 10／任意 10），
         本工具算出的面板列與 resultsAFC/panel.csv.gz 對應列【逐欄逐位元】相同；
         再對 8 檔追蹤股 ＋ 抽到的股票做【全歷史】逐列比對，並比 build_sig_gate_b（真價格）的輸出整張相同。
         ⭐ 面板是在 gate3 全體上建的、本工具只算少數幾檔 ⇒ 相同 ＝ 門檻B 沒有橫斷面量的實證。
 B 曾觸發：數個過去的 asof，事件表的（觸發量測日、進場根、出場根、進場日、出場日、第幾個交易日）
         與 build_sig_gate_b（AFC 面板、真價格）的 entry_pos／xpos 一致；entry_open_ok＝F 的恰好是它剔掉的。
         asof＝資料末日：出場根在日曆內的比 build_sig_gate_b，超出日曆的驗「出場根 ＝ 持有 120 根」。
 C 無前視：asof 之後的價量／法人／股數／月營收亂改（V2 連還原因子也改），逐檔表與事件表不變；
         ⭐ 並先證明亂改真的被讀到（asof 之後的原始特徵確實變了）⇒ 這道測試不是空轉。
 D 日曆外推：用休市表從 2021 起外推到資料末日，每個實際交易日都要被預測到（多預測的＝臨時休市，列出）。
 E 母體外：興櫃／存託憑證／查無代號 ⇒「不在門檻B 母體」。
 F 交件重現：resultsGB/gate_b_status_20260924.csv 與重跑逐字相同。
"""
from __future__ import annotations

import os
import shutil
import sys
import tempfile
import time

sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
import gate_b_status as GB                    # noqa: E402  （import 時 D.DATA 指到 main edc6f8002f 快照）
import numpy as np                            # noqa: E402
import pandas as pd                           # noqa: E402
from backtest import researchp1 as P1         # noqa: E402
from backtest import research34 as R34        # noqa: E402

D, P, P7 = GB.D, GB.P, GB.P7
SEED = 20260925
PANEL = "backtest/resultsAFC/panel.csv.gz"
PANEL_END = "2026-03-31"
XCOL = GB.XCOL
TMP_ROOT = os.environ.get("GB_TMP") or None
FAIL: list[str] = []


def check(cond, msg):
    print(("  ✓ " if cond else "  ✗ ") + msg, flush=True)
    if not cond:
        FAIL.append(msg)


def same_val(a, b) -> bool:
    na, nb = pd.isna(a), pd.isna(b)
    if na or nb:
        return bool(na and nb)
    if isinstance(a, (str, pd.Timestamp)) or isinstance(b, (str, pd.Timestamp)):
        return str(a) == str(b)
    return float(a) == float(b)


def diff_frames(mine: pd.DataFrame, ref: pd.DataFrame, cols) -> tuple[int, list]:
    """(對到的列數, 不一致清單)；列集合不同也算不一致。"""
    k = ["stock_id", "measure_date"]
    m = mine.merge(ref, on=k, how="outer", suffixes=("_m", "_r"), indicator=True)
    bad = [("列集合", r.stock_id, r.measure_date, r._merge) for r in m[m["_merge"] != "both"].itertuples()]
    b = m[m["_merge"] == "both"]
    for c in cols:
        if c in k:
            continue
        a_ = b[c + "_m"] if c + "_m" in b else pd.Series(np.nan, index=b.index)
        r_ = b[c + "_r"] if c + "_r" in b else pd.Series(np.nan, index=b.index)
        for i in b.index:
            if not same_val(a_[i], r_[i]):
                bad.append((c, b.at[i, "stock_id"], b.at[i, "measure_date"], a_[i], r_[i]))
    return len(b), bad


def sig_key(s: pd.DataFrame) -> pd.DataFrame:
    return s.sort_values(["sid", "entry_pos"]).reset_index(drop=True)


# ───────────────────────── A 回歸 ─────────────────────────
def t_regress(cal, U, panel, uni):
    print("\n=== A 回歸：本工具的面板列 vs resultsAFC/panel.csv.gz ===")
    rng = np.random.default_rng(SEED)
    pm = panel[panel["measure_date"] <= pd.Timestamp(PANEL_END)].copy()
    pm["month"] = pm["measure_date"].dt.strftime("%Y-%m")
    s_dummy = GB.signal_rows(pm, cal)                       # 分層用：純訊號（全 1 假價格）
    skeys = set(zip(s_dummy["sid"], s_dummy["month"]))
    is_sig = np.array([(s, m) in skeys for s, m in zip(pm["stock_id"], pm["month"])])
    pools = [pm[is_sig], pm[pm["eligible"].astype(bool) & ~is_sig], pm]
    picks = []
    for pool in pools:
        if picks:
            taken = set(picks)
            pool = pool[[(a, b) not in taken for a, b in zip(pool["stock_id"], pool["measure_date"])]]
        idx = rng.choice(len(pool), size=10, replace=False)
        picks += list(zip(pool["stock_id"].iloc[idx], pool["measure_date"].iloc[idx]))
    check(len(set(picks)) == 30, f"抽到 30 個不重複（股, 量測日）：訊號 10／合格非訊號 10／任意 10（種子 {SEED}）")
    pos_of = {d: i for i, d in enumerate(cal)}
    cols = list(panel.columns)
    mine = []
    for sid in sorted({s for s, _ in picks}):
        ps = sorted(pos_of[d] for s, d in picks if s == sid)
        mine.append(GB.panel_rows([sid], cal, ps, U))
    mine = pd.concat(mine, ignore_index=True)
    ref = panel.set_index(["stock_id", "measure_date"]).loc[picks].reset_index()
    n, bad = diff_frames(mine, ref, cols)
    check(n == 30 and not bad, f"30 個（股, 量測日）× {len(cols)} 欄逐位元相同（對到 {n} 列；不一致 {len(bad)}：{bad[:3]}）")
    n_sig_pick = sum((s, d.strftime("%Y-%m")) in skeys for s, d in picks)
    check(n_sig_pick >= 10, f"抽樣含訊號列 {n_sig_pick} 個（⛔ 全是非訊號列就驗不到訊號那一側）")

    sids_full = list(dict.fromkeys(list(GB.TRACK) + sorted({s for s, _ in picks})))
    positions_all = P.measurement_days(cal, "2015-01-01", PANEL_END)
    t0 = time.time()
    mine_full = GB.panel_rows(sids_full, cal, positions_all, U)
    ref_full = panel[panel["stock_id"].isin(sids_full) & (panel["measure_date"] <= pd.Timestamp(PANEL_END))]
    n, bad = diff_frames(mine_full, ref_full, cols)
    check(n == len(ref_full) == len(mine_full) and not bad,
          f"全歷史 {len(sids_full)} 檔（8 檔追蹤 ＋ 抽到的）{len(positions_all)} 個量測日：{n:,} 列 × {len(cols)} 欄逐位元相同"
          f"（不一致 {len(bad)}：{bad[:3]}；{time.time() - t0:.0f}s）")
    closes, opens = P1.load_prices(sids_full, cal, uni)     # ⭐ researchp1.load_prices 本身（快取目錄已指到暫存）
    s_ref = P7.build_sig_gate_b(ref_full, cal, closes, opens)
    s_mine = P7.build_sig_gate_b(mine_full, cal, closes, opens)
    check(len(s_ref) > 0 and sig_key(s_ref).equals(sig_key(s_mine)),
          f"build_sig_gate_b（真價格）在本工具的列與 AFC 面板列上輸出整張相同（{len(s_ref)} 筆、{s_ref['sid'].nunique()} 檔）")
    check(all(ref_full["stock_id"].isin(set(U["stock_id"]))),
          "⭐ AFC 面板在 gate3 全體上建、本工具只算這幾檔 ⇒ 仍逐位元相同 ⇒ 門檻B 用到的欄沒有橫斷面量")
    return sids_full, s_ref, positions_all, closes, opens


# ───────────────────────── B 曾觸發 ─────────────────────────
def t_triggers(cal, U, sids_full, s_ref, positions_all, closes, opens):
    print("\n=== B 曾觸發：事件表 vs build_sig_gate_b 的 entry_pos／xpos ===")
    month_pos = {cal[p].strftime("%Y-%m"): int(p) for p in positions_all}
    ref = s_ref.copy()
    ref["mpos"] = ref["month"].map(month_pos)
    n_cmp = 0
    for asof in ("2024-06-28", "2025-10-15", "2026-03-31"):
        asof_pos = int(cal.searchsorted(pd.Timestamp(asof), side="right")) - 1
        tab, ev = GB.gate_b_status(sids_full, asof)
        w = ev[ev["in_window_120"].astype(bool)].copy()
        w["month"] = pd.to_datetime(w["measure_date"]).dt.strftime("%Y-%m")
        mine_T = set(zip(w.loc[w["entry_open_ok"] == "T", "stock_id"], w.loc[w["entry_open_ok"] == "T", "month"],
                         w.loc[w["entry_open_ok"] == "T", "entry_pos"].astype(int), w.loc[w["entry_open_ok"] == "T", XCOL].astype(int)))
        rw = ref[(ref["mpos"] >= asof_pos - GB.WINDOW + 1) & (ref["mpos"] <= asof_pos)]
        ref_set = set(zip(rw["sid"], rw["month"], rw["entry_pos"].astype(int), rw[XCOL].astype(int)))
        check(len(ref_set) > 0 and mine_T == ref_set,
              f"asof {asof}：窗內觸發 {len(w)} 筆，其中可進場 {len(mine_T)} 筆 ＝ build_sig_gate_b 的 {len(ref_set)} 筆（股、月、entry_pos、xpos 全同）")
        f = w[w["entry_open_ok"] == "F"]
        f_ok = all((not np.isfinite(float(opens[s][int(e)]))) or float(opens[s][int(e)]) <= 0 for s, e in zip(f["stock_id"], f["entry_pos"]))
        check(f_ok and not (set(zip(f["stock_id"], f["month"])) & set(zip(rw["sid"], rw["month"]))),
              f"asof {asof}：entry_open_ok＝F 的 {len(f)} 筆恰好是進場根開盤缺／≤0 而被 build_sig_gate_b 剔掉的")
        ok_dates = all(pd.Timestamp(r.entry_date) == cal[int(r.entry_pos)] and pd.Timestamp(r.exit_date) == cal[int(getattr(r, XCOL))]
                       and r.exit_date_basis == "資料日曆" for r in w.itertuples())
        ok_dayn = all(int(r.day_n) == asof_pos - int(r.entry_pos) + 1 for r in w.itertuples() if int(r.entry_pos) <= asof_pos)
        ok_hold = all(int(getattr(r, XCOL)) == D.exit_pos(int(r.entry_pos), P7.HOLD_BARS_N) for r in w.itertuples())
        check(ok_dates and ok_dayn and ok_hold, f"asof {asof}：進場日＝日曆[entry_pos]、出場日＝日曆[xpos]、第幾個交易日＝asof_pos−entry_pos+1、xpos＝D.exit_pos(entry, {P7.HOLD_BARS_N})")
        extra = ev[~ev["in_window_120"].astype(bool)]
        check(all(cal.get_loc(pd.Timestamp(d)) == asof_pos - GB.WINDOW for d in extra["measure_date"]),
              f"asof {asof}：窗外多列的 {len(extra)} 筆只可能是量測日 ＝ asof_pos − 120（第二種讀法）")
        cnt = w.groupby("stock_id").size()
        check(all(int(tab.set_index("stock_id").at[s, "n_trig_120d"]) == int(cnt.get(s, 0)) for s in sids_full),
              f"asof {asof}：逐檔表 n_trig_120d 與事件表一致")
        n_cmp += len(ref_set)
    check(n_cmp >= 10, f"B 總共比了 {n_cmp} 筆觸發（⛔ 太少就沒有鑑別力）")

    # asof ＝ 資料末日：出場根在日曆內的 ⇒ 比 build_sig_gate_b（真價格、真日曆）；超出的 ⇒ 驗持有 120 根與依據字樣
    asof = str(cal[-1].date()); asof_pos = len(cal) - 1
    tab, ev = GB.gate_b_status(sids_full, asof)
    lo = asof_pos - GB.WINDOW
    rows = GB.panel_rows(sids_full, cal, P.measurement_days(cal, str(cal[lo].date()), asof), U)
    s_now = P7.build_sig_gate_b(rows, cal, closes, opens)
    in_cal = ev[ev[XCOL].astype(int) < len(cal)]
    out_cal = ev[ev[XCOL].astype(int) >= len(cal)]
    a = set(zip(in_cal.loc[in_cal["entry_open_ok"] == "T", "stock_id"], in_cal.loc[in_cal["entry_open_ok"] == "T", "entry_pos"].astype(int),
                in_cal.loc[in_cal["entry_open_ok"] == "T", XCOL].astype(int)))
    b = set(zip(s_now["sid"], s_now["entry_pos"].astype(int), s_now[XCOL].astype(int))) if len(s_now) else set()
    check(a == b, f"asof {asof}：出場根在日曆內的 {len(in_cal)} 筆 ＝ build_sig_gate_b 的 {len(b)} 筆")
    check(all(int(r[XCOL]) == D.exit_pos(int(r["entry_pos"]), P7.HOLD_BARS_N) and r["exit_date_basis"] != "資料日曆"
              for _, r in out_cal.iterrows()),
          f"asof {asof}：出場根超出日曆的 {len(out_cal)} 筆 xpos＝D.exit_pos(entry, 120)、出場日標為外推")
    check(all(int(r.day_n) == 0 and r.entry_open_ok == "未到" for r in ev.itertuples() if int(r.entry_pos) > asof_pos)
          and all(int(r.day_n) == asof_pos - int(r.entry_pos) + 1 for r in ev.itertuples() if int(r.entry_pos) <= asof_pos),
          f"asof {asof}：進場根在 asof 之後 ⇒ day_n＝0、entry_open_ok＝未到；其餘 day_n＝asof_pos−entry_pos+1")

    # ⭐ entry_open_ok＝F 那條路在真資料上一筆都沒碰到 ⇒ 造 fixture：把某筆觸發的【進場日那一列】從日檔刪掉（＝ 進場日停牌）
    #   ⇒ 訊號仍是 T（量測日的資料沒動），entry_open_ok 要變 F，而且 build_sig_gate_b（真價格）要剔掉它
    asof = "2026-03-31"; asof_pos = int(cal.searchsorted(pd.Timestamp(asof), side="right")) - 1
    _, ev = GB.gate_b_status(sids_full, asof)
    t = ev[ev["in_window_120"].astype(bool) & (ev["entry_open_ok"] == "T")].iloc[0]
    sid, ent = t["stock_id"], cal[int(t["entry_pos"])]
    src = D.DATA
    dst = tempfile.mkdtemp(prefix="gb_fx_", dir=TMP_ROOT)
    try:
        dd = os.path.join(dst, "data")
        for sub in ("meta", "stocks", "stocks_inst", "adj"):
            os.makedirs(os.path.join(dd, sub))
        for f in ("calendar_twse.csv", "stocks.csv", "industry.csv", "holiday_schedule.csv"):
            shutil.copy(os.path.join(src, "meta", f), os.path.join(dd, "meta", f))
        shutil.copytree(os.path.join(src, "mops", "revenue_hist"), os.path.join(dd, "mops", "revenue_hist"))
        for sub in ("stocks_inst", "adj"):
            if os.path.exists(os.path.join(src, sub, f"{sid}.csv")):
                shutil.copy(os.path.join(src, sub, f"{sid}.csv"), os.path.join(dd, sub, f"{sid}.csv"))
        df = pd.read_csv(os.path.join(src, "stocks", f"{sid}.csv"), dtype=str)
        df[pd.to_datetime(df["date"]) != ent].to_csv(os.path.join(dd, "stocks", f"{sid}.csv"), index=False)
        D.DATA = dd
        tab1, ev1 = GB.gate_b_status([sid], asof)
        _, U1 = GB.load_gate3()
        rows1 = GB.panel_rows([sid], cal, P.measurement_days(cal, str(cal[asof_pos - GB.WINDOW].date()), asof), U1)
        c1 = pd.Series(D.load_stock(sid, U1.set_index("stock_id")["market"][sid], cal).df["close"].to_numpy()).ffill().to_numpy(np.float32)
        o1 = D.load_stock(sid, U1.set_index("stock_id")["market"][sid], cal).df["open"].to_numpy(np.float32)
        s1 = P7.build_sig_gate_b(rows1, cal, {sid: c1}, {sid: o1})
    finally:
        D.DATA = src
        shutil.rmtree(dst, ignore_errors=True)
    r1 = ev1[pd.to_datetime(ev1["measure_date"]) == pd.Timestamp(t["measure_date"])]
    dropped = len(s1) == 0 or int(t["entry_pos"]) not in set(s1.loc[s1["sid"] == sid, "entry_pos"].astype(int))
    check(len(r1) == 1 and r1["entry_open_ok"].iloc[0] == "F" and dropped,
          f"fixture：{sid} 刪掉進場日 {ent.date()} 那一列 ⇒ 事件仍在、entry_open_ok＝F、build_sig_gate_b（真價格）剔掉它")


# ───────────────────────── C 無前視 ─────────────────────────
def _perturb(src, dst, sids, asof_pos, cal, rng, adj_mode: bool):
    asof = cal[asof_pos]
    os.makedirs(os.path.join(dst, "meta"))
    for f in ("calendar_twse.csv", "stocks.csv", "industry.csv", "holiday_schedule.csv"):
        shutil.copy(os.path.join(src, "meta", f), os.path.join(dst, "meta", f))
    for sub in ("stocks", "stocks_inst", "adj", os.path.join("mops", "revenue_hist")):
        os.makedirs(os.path.join(dst, sub))
    for sid in sids:
        p = os.path.join(src, "stocks", f"{sid}.csv")
        df = pd.read_csv(p, dtype=str)
        fut = (pd.to_datetime(df["date"]) > asof).to_numpy()
        n = int(fut.sum())
        for c in ("open", "high", "low", "close"):
            df.loc[fut, c] = (pd.to_numeric(df.loc[fut, c], errors="coerce") * rng.uniform(0.6, 1.4, n)).round(2).astype(str)
        for c in ("volume", "amount", "shares"):
            df.loc[fut, c] = (pd.to_numeric(df.loc[fut, c], errors="coerce") * rng.uniform(0.0, 3.0, n)).round(0).astype(str)
        drop = np.flatnonzero(fut)[rng.random(n) < 0.15]
        df.drop(index=df.index[drop]).to_csv(os.path.join(dst, "stocks", f"{sid}.csv"), index=False)
        p = os.path.join(src, "stocks_inst", f"{sid}.csv")
        if os.path.exists(p):
            di = pd.read_csv(p, dtype=str)
            fi = (pd.to_datetime(di["date"]) > asof).to_numpy(); m = int(fi.sum())
            for c in ("foreign", "trust"):
                di.loc[fi, c] = rng.integers(-5_000_000, 5_000_000, m).astype(str)
            drop = np.flatnonzero(fi)[rng.random(m) < 0.15]
            di.drop(index=di.index[drop]).to_csv(os.path.join(dst, "stocks_inst", f"{sid}.csv"), index=False)
        p = os.path.join(src, "adj", f"{sid}.csv")
        if os.path.exists(p) or adj_mode:
            a = pd.read_csv(p, dtype=str) if os.path.exists(p) else pd.DataFrame(columns=["date", "factor", "factor_official", "cum_factor", "pre_close", "ref_price", "kind", "event"])
            if adj_mode:
                # ⭐ 未來除權息／減資：asof 之後的因子亂改 ＋ 多一個假事件 ⇒ 依 cum_factor 的定義（該列含之後的因子連乘）重算
                fac = pd.to_numeric(a["factor"], errors="coerce").to_numpy(float)
                dts = pd.to_datetime(a["date"]).to_numpy()
                fut_a = dts > np.datetime64(asof)
                old_fut = float(np.prod(fac[fut_a])) if fut_a.any() else 1.0
                fac = np.where(fut_a, fac * rng.uniform(0.7, 1.0, len(fac)), fac)
                new_row = {"date": str(cal[min(asof_pos + 3, len(cal) - 1)].date()), "factor": "0.8", "factor_official": "",
                           "cum_factor": "", "pre_close": "", "ref_price": "", "kind": "息", "event": "exright"}
                a = pd.concat([a, pd.DataFrame([new_row])], ignore_index=True)
                fac = np.r_[fac, 0.8]; fut_a = np.r_[fut_a, True]
                a["factor"] = [f"{x:.8f}" for x in fac]
                a = a.assign(_d=pd.to_datetime(a["date"])).sort_values("_d", kind="stable").drop(columns="_d").reset_index(drop=True)
                fac = pd.to_numeric(a["factor"]).to_numpy(float)
                fut_a = (pd.to_datetime(a["date"]) > asof).to_numpy()
                cum_old = pd.to_numeric(a["cum_factor"], errors="coerce").to_numpy(float)
                g = float(np.prod(fac[fut_a])) / old_fut
                cum = np.where(fut_a, np.cumprod(fac[::-1])[::-1], cum_old * g)
                a["cum_factor"] = [f"{x:.8f}" for x in cum]
            a.to_csv(os.path.join(dst, "adj", f"{sid}.csv"), index=False)
    rd = None
    for f in sorted(os.listdir(os.path.join(src, "mops", "revenue_hist"))):
        df = pd.read_csv(os.path.join(src, "mops", "revenue_hist", f), dtype=str)
        if rd is None:
            rd = {}
        pers = sorted(set(df["period"].dropna()))
        rdm = R34.rebalance_dates(pers, cal, GB.PUB_DAY)
        fut_p = {p for p in pers if p not in rdm or rdm[p][1] > asof_pos}
        mk = df["stock_id"].isin(set(sids)) & df["period"].isin(fut_p)
        k = int(mk.sum())
        if k:
            v = pd.to_numeric(df.loc[mk, "當月營收"], errors="coerce") * rng.uniform(0.2, 5.0, k)
            v = v.round(0).astype("Int64").astype(str)
            v[rng.random(k) < 0.3] = ""
            df.loc[mk, "當月營收"] = v.to_numpy()
        df.to_csv(os.path.join(dst, "mops", "revenue_hist", f), index=False)


def t_lookahead(cal, sids):
    print("\n=== C 無前視：asof 之後亂改，結果不變 ===")
    src = D.DATA
    for asof in ("2026-06-15", "2026-09-01"):
        asof_pos = int(cal.searchsorted(pd.Timestamp(asof), side="right")) - 1
        tab0, ev0 = GB.gate_b_status(sids, asof)
        U = GB.load_gate3()[1].set_index("stock_id")["market"]
        for adj_mode, tag in ((False, "V1 價量／法人／股數／營收"), (True, "V2 ＋還原因子（未來除權息）")):
            dst = tempfile.mkdtemp(prefix="gb_la_", dir=TMP_ROOT)
            try:
                _perturb(src, os.path.join(dst, "data"), sids, asof_pos, cal, np.random.default_rng(SEED + asof_pos + adj_mode), adj_mode)
                D.DATA = os.path.join(dst, "data")
                # ⭐ 先證明亂改真的被讀到：asof 之後的原始特徵要變；V1 另驗 asof 以前逐位元不變
                live, pre_same = 0, 0
                for s in sids:
                    D.DATA = src; r0 = P.stock_raw(s, U[s], cal)
                    D.DATA = os.path.join(dst, "data"); r1 = P.stock_raw(s, U[s], cal)
                    a0, a1 = r0["amt20"].to_numpy()[asof_pos + 1:], r1["amt20"].to_numpy()[asof_pos + 1:]
                    live += int(not np.array_equal(a0, a1, equal_nan=True))
                    cols = ["amt20", "ma_stack", "ma60_up", "fore20", "trust20", "bars", "close"]
                    pre_same += int(all(np.array_equal(r0[c].to_numpy(float)[:asof_pos + 1], r1[c].to_numpy(float)[:asof_pos + 1], equal_nan=True) for c in cols))
                check(live == len(sids), f"asof {asof} {tag}：{live}/{len(sids)} 檔 asof 之後的 amt20 確實變了（⇒ 亂改有被讀到，測試不空轉）")
                if not adj_mode:
                    check(pre_same == len(sids), f"asof {asof} {tag}：{pre_same}/{len(sids)} 檔 asof 以前的原始特徵逐位元不變")
                tab1, ev1 = GB.gate_b_status(sids, asof)
            finally:
                D.DATA = src
                shutil.rmtree(dst, ignore_errors=True)
            same_tab = tab0.astype(str).equals(tab1.astype(str))
            same_ev = ev0.astype(str).reset_index(drop=True).equals(ev1.astype(str).reset_index(drop=True))
            check(same_tab and same_ev, f"asof {asof} {tag}：逐檔表（{len(tab0)} 檔、訊號 T {int((tab0['signal'] == 'T').sum())}）"
                                        f"與事件表（{len(ev0)} 筆）完全不變")
        if asof == "2026-09-01":
            check((tab0["measure_date"] == "2026-09-01").all(), "asof 恰為量測日 ⇒ 用當天（量測日收盤判、次日開盤進）")


# ───────────────────────── D 日曆外推 ─────────────────────────
def t_calendar(cal):
    print("\n=== D 預計出場日的日曆外推 vs 實際交易日曆 ===")
    base = cal[cal <= pd.Timestamp("2020-12-31")]
    act = cal[cal > pd.Timestamp("2020-12-31")]
    fut, basis = GB.future_trading_days(base, len(act) + 60)
    proj = set(fut[fut <= cal[-1]])
    missed = sorted(set(act) - proj)
    extra = sorted(proj - set(act))
    check(not missed, f"2021-01～{cal[-1].date()} 每個實際交易日都被外推到（漏 {len(missed)}：{[str(d.date()) for d in missed[:5]]}）")
    print(f"     外推多出來的日子（颱風假，或休市表沒列的封關結算日）{len(extra)} 天：{[str(d.date()) for d in extra]}")
    check(len(extra) <= 12, f"外推多出的日子只有少數（{len(extra)} 天）⇒ 外推的出場日可能偏早、⛔ 不會偏晚")
    check(set(basis[:len(proj)]) == {"休市表外推"}, "2021～2026 的依據字樣都是「休市表外推」（該年休市表已公告）")


# ───────────────────────── E 母體外 ─────────────────────────
def t_outside():
    print("\n=== E 母體外 ⇒ 不在門檻B 母體 ===")
    stocks = pd.read_csv(os.path.join(D.DATA, "meta", "stocks.csv"), dtype=str)
    esb = stocks.loc[stocks["market"] == "emerging", "stock_id"].iloc[0]
    dr = stocks.loc[stocks["kind"] == "dr", "stock_id"].iloc[0]
    tab, _ = GB.gate_b_status([esb, dr, "0000Z", "2609"], str(D.load_calendar()[-1].date()))
    st = tab.set_index("stock_id")["status"]
    check(st[esb].startswith(GB.NOT_IN) and "興櫃" in st[esb], f"興櫃 {esb} ⇒ {st[esb]}")
    check(st[dr].startswith(GB.NOT_IN), f"存託憑證 {dr} ⇒ {st[dr]}")
    check(st["0000Z"].startswith(GB.NOT_IN) and "查無" in st["0000Z"], f"查無代號 0000Z ⇒ {st['0000Z']}")
    check(st["2609"] == "已判定", "同一趟裡的母體內股票照常判定（2609）")


# ───────────────────────── F 交件重現 ─────────────────────────
def t_deliverable(cal):
    print("\n=== F 交件重現 ===")
    p = os.path.join(GB.OUT, "gate_b_status_20260924.csv")
    if not os.path.exists(p):
        check(False, f"找不到交件 {p}")
        return
    tab, ev = GB.gate_b_status(GB.TRACK, "2026-09-24")
    old = pd.read_csv(p, dtype=str, keep_default_na=False)
    new = pd.read_csv(__import__("io").StringIO(tab.to_csv(index=False)), dtype=str, keep_default_na=False)
    check(old.equals(new), f"{p} 與重跑逐字相同")
    pe = os.path.join(GB.OUT, "gate_b_events_20260924.csv")
    olde = pd.read_csv(pe, dtype=str, keep_default_na=False)
    newe = pd.read_csv(__import__("io").StringIO(ev.to_csv(index=False)), dtype=str, keep_default_na=False)
    check(olde.equals(newe), f"{pe} 與重跑逐字相同")


def main():
    t0 = time.time()
    cal = D.load_calendar()
    check(GB.H2.SHA.startswith("edc6f8002f") and D.DATA == GB.H2.H2D, f"資料＝main 快照 {GB.H2.SHA[:10]}（D.DATA＝{D.DATA}）")
    _, U = GB.load_gate3()
    panel = P.read_panel(PANEL)
    uni = D.load_universe().set_index("stock_id")["market"]
    reg = tempfile.mkdtemp(prefix="gb_p1_", dir=TMP_ROOT)
    P1.REG = reg                                   # ⭐ 價格快取寫進暫存目錄（⛔ 不讀舊快照的 resultsp1/regress 快取）
    try:
        sids_full, s_ref, positions_all, closes, opens = t_regress(cal, U, panel, uni)
        t_triggers(cal, U, sids_full, s_ref, positions_all, closes, opens)
        t_lookahead(cal, sids_full)
        t_calendar(cal)
        t_outside()
        t_deliverable(cal)
    finally:
        shutil.rmtree(reg, ignore_errors=True)
    print(f"\n{'✅ 全部通過' if not FAIL else f'⛔ {len(FAIL)} 條沒過'}（{time.time() - t0:.0f}s）")
    if FAIL:
        sys.exit(1)


if __name__ == "__main__":
    main()

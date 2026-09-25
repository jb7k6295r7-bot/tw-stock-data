# -*- coding: utf-8 -*-
"""門檻B 逐檔判定（情報線 1603）——給情報線呼叫的 `gate_b_status(sids, asof)` ＋ 逐檔表。

    ~/tw-p16/.venv/bin/python backtest/gate_b_status.py [--asof 2026-09-24] [--sids 2609,6209,...] [--out backtest/resultsGB]

⭐ 定義一律照既有程式，⛔ 本檔不寫第二套（本檔只做「挑股、挑量測日、呼叫、排版」）：
  資料    researchH2（main edc6f8002f 快照；import 時 D.DATA 指到 ~/h2data/<sha>/data）
  母體    universe_gate.gate3(meta/stocks.csv) ∩ data.load_universe()（＝ researchAFC_panel 同一式）
  面板列  researchp4.panel_worker（＝ build_panel 的逐檔工人，⛔ 不另寫）：eligible ＝ liq_ok ∧ bars_ok ∧ inst_ok；
          min_periods 常設斷言照開（mp_check=True），不一致 > 0 ⇒ 停（與 researchAFC_panel 同）
          rev_hi24 ＝ p4_features.rev_hi24_flags，pub_day／incl_current 取 build_panel 的預設值（inspect 讀，⛔ 不抄常數）
  量測日  p4_features.measurement_days（每月第一個交易日）
  訊號    researchp7.build_sig_gate_b(signal="B")：eligible ∧ rev_hi24＝100 ∧ ma60_up＝100 ∧ ma_stack＝0；
          進場根＝量測日次一交易日（entry_pos）、出場根＝xpos_H120（D.exit_pos，持有 120 根；進場那根算第 1 根）
⭐ 門檻B 沒有任何橫斷面量：三閘（amt20 ≥ 5,000 萬的絕對值、bars ≥ 120、法人 20 日可算）與三條布林全是逐檔自己的量，
  build_sig_gate_b 檔頭也寫「零橫斷面百分位」（百分位只出現在 researchp4.classify，門檻B 不走它）
  ⇒ 只算要的股票即可，⛔ 不必在 gate3 全體上重建面板；selftest 以「只算少數幾檔 ＝ gate3 全體面板」逐位元驗這件事。

落地讀法（⛔ 在看任何結果之前寫定）：
 L1 「訊號 T/F」取自 build_sig_gate_b 本身：以【全 1 的假價格】呼叫 ⇒ 它的價格剔除條件一條都不觸發
    ⇒ 回傳列 ＝ eligible ∧ 三條布林 ⇒ ⛔ 本檔沒有第二份訊號條件式。
    真價格的剔除（進場根開盤缺／≤0）另報 entry_open_ok：進場根在 asof 之後 ⇒「未到」（⛔ 不偷看）。
 L2 「最近 120 個交易日內曾觸發」＝ 觸發量測日落在 [asof_pos − 119, asof_pos]（asof 當日算第 1 個交易日）。
    另一種讀法「asof 當日仍在持有期內」⇔ 量測日 ≥ asof_pos − 120，多含 asof_pos − 120 那一天
    ⇒ events 表把那一天也列出來，並給 in_window_120／holding_on_asof 兩欄，讓讀的人自己挑。
 L3 「第幾個交易日」＝ asof 是該筆持有期的第幾根（進場那根算第 1 根，與 build_sig_gate_b「持有 120 根」同一數法）；
    進場根在 asof 之後 ⇒ 0（＝ 尚未進場，下一個交易日開盤進）。
 L4 預計出場日 ＝ 日曆[xpos_H120]。xpos 超出資料日曆 ⇒ 以 meta/holiday_schedule.csv 外推（平日 − 已公告休市日 ＋ 已公告交易日）；
    休市表沒涵蓋的年度只扣週末 ⇒ exit_date_basis 標明；颱風等臨時休市不可預知。
 L5 量測日當天無成交（或不在籍）⇒ panel_worker 不產列 ⇒ 該檔當月「無判定」（⛔ 不寫 F，也不寫 T）。
 L6 asof 之後的資料不進判定（stock_raw 全部是回看、rev_hi24 在可得日才生效）；selftest 以「asof 之後亂改、結果不變」驗。
"""
from __future__ import annotations

import argparse
import contextlib
import inspect
import io
import os
import sys

sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
import researchH2 as H2                       # noqa: E402  把 D.DATA 指到快照（並 chdir 到 ~/tw-p17）
import numpy as np                            # noqa: E402
import pandas as pd                           # noqa: E402
from backtest import data as D                # noqa: E402
from backtest import p4_features as P         # noqa: E402
from backtest import research34 as R34        # noqa: E402
from backtest import researchp4 as RP4        # noqa: E402
from backtest import researchp7 as P7         # noqa: E402
from backtest import universe_gate as UG      # noqa: E402

TRACK = ("2609", "6209", "3535", "4164", "6282", "6443", "8289", "6469")   # 情報線 1603 的追蹤 8 檔
WINDOW = 120
OUT = "backtest/resultsGB"
XCOL = f"xpos_{P7.RULE}"
SIG_START = inspect.signature(P7.build_sig_gate_b).parameters["start"].default    # "2017-01-01"（⛔ 不抄常數）
_BP = inspect.signature(RP4.build_panel).parameters
PUB_DAY, REV_INCL_CURRENT = _BP["pub_day"].default, _BP["rev_incl_current"].default
NOT_IN = "不在門檻B 母體"
NOTES = ["曾觸發 ≠ 會買到（W1 每月量測日判、8 檔名額隨機挑、抱 120 個交易日）",
         "只在每月量測日判一次，量測日之間不換判定",
         "ma_stack 條件是等於 0（不是多頭排列）"]


def load_gate3() -> tuple[pd.DataFrame, pd.DataFrame]:
    """(meta/stocks.csv 全表, gate3 ∩ load_universe)——與 researchAFC_panel 同一式；讀 D.DATA（⭐ 跟著指標走，selftest 會換）。"""
    stocks = pd.read_csv(os.path.join(D.DATA, "meta", "stocks.csv"), dtype=str)
    with contextlib.redirect_stdout(io.StringIO()):
        g = UG.gate3(stocks)
    U = D.load_universe().merge(g[["stock_id"]], on="stock_id")
    return stocks, U


def why_not_in_universe(sid: str, stocks: pd.DataFrame) -> str:
    """只給【顯示用】的原因字樣；⛔ 是不是母體一律由 gate3 決定（本函式不參與判定）。"""
    r = stocks[stocks["stock_id"] == sid]
    if r.empty:
        return "查無代號（meta/stocks.csv 沒有）"
    r = r.iloc[0]
    if r["market"] == "emerging":
        return "興櫃"
    if r["kind"] != "stock" or r["market"] not in ("twse", "tpex"):
        return f"非上市櫃普通股（market={r['market']}、kind={r['kind']}）"
    if "-DR" in str(r["name"]):
        return "名稱含 -DR"
    if "-創" in str(r["name"]):
        return "創新板（名稱含 -創）"
    return "不在 gate3"


def panel_rows(sids, cal: pd.DatetimeIndex, positions, U: pd.DataFrame) -> pd.DataFrame:
    """指定股票 × 指定量測日的面板列 ＝ researchp4.panel_worker 的輸出（⛔ 逐欄照原程式，含 fwd_* 與 inst_win_*）。
    rev_hi24 旗標逐檔獨立（p4_features.rev_hi24_flags 對每一欄各自迴圈）⇒ 只取要的欄算，結果與全體算相同。"""
    sids = [s for s in dict.fromkeys(sids)]
    tdr = P.load_tdr_codes()
    rev, _, _ = R34.load_revenue()
    rev = rev[[s for s in sids if s in rev.columns]]
    rev_flags = P.rev_hi24_flags(rev, cal, PUB_DAY, incl_current=REV_INCL_CURRENT, undecided=tdr)
    RP4._init(cal, rev_flags, np.asarray(positions), True)
    rows, mism = [], []
    for r in U[U["stock_id"].isin(set(sids))].itertuples():
        rs, ms = RP4.panel_worker((r.stock_id, r.market, r.first_seen, r.last_seen))
        rows.extend(rs); mism.extend(ms)
    if mism:
        raise SystemExit(f"⛔ min_periods 常設斷言不成立（{len(mism)} 列）⇒ 停：{mism[:3]}")
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    df["measure_date"] = pd.to_datetime(df["measure_date"])
    return df.sort_values(["measure_date", "stock_id"]).reset_index(drop=True)


def future_trading_days(cal: pd.DatetimeIndex, n: int) -> tuple[pd.DatetimeIndex, list[str]]:
    """cal 最後一天之後的 n 個【預計】交易日：平日 − 休市表的休市日 ＋ 休市表的交易日（名稱含「開始交易／最後交易」）。
    回 (日期, 每一天的依據字樣)。⚠ 休市表未涵蓋的年度只扣週末；颱風假不可預知。"""
    hs = pd.read_csv(os.path.join(D.DATA, "meta", "holiday_schedule.csv"), dtype=str)
    hs = hs[hs["date"].astype(str).str.match(r"^\d{4}-\d{2}-\d{2}$", na=False)]
    d = pd.to_datetime(hs["date"])
    trade = hs["name"].fillna("").str.contains("開始交易|最後交易").to_numpy()
    closed, opened = set(d[~trade]), set(d[trade])
    covered = int(d.dt.year.max())
    out, basis = [], []
    x = cal[-1]
    while len(out) < n:
        x = x + pd.Timedelta(days=1)
        if (x.weekday() < 5 and x not in closed) or x in opened:
            out.append(x)
            basis.append("休市表外推" if x.year <= covered else f"只扣週末（{x.year} 年休市表未公告）")
    return pd.DatetimeIndex(out), basis


def signal_rows(rows: pd.DataFrame, cal_ext: pd.DatetimeIndex, opens: dict | None = None) -> pd.DataFrame:
    """呼叫 researchp7.build_sig_gate_b(signal="B")。closes 一律全 1；opens 預設全 1（⇒ 價格剔除全不觸發 ⇒ 純訊號，L1）。"""
    cols = ["sid", "entry_pos", XCOL, f"g_{P7.RULE}", "month", "relvol", "vol"]
    if rows.empty:
        return pd.DataFrame(columns=cols)
    one = np.ones(len(cal_ext))
    sids = sorted(rows["stock_id"].unique())
    closes = {s: one for s in sids}
    op = {s: (opens[s] if opens is not None else one) for s in sids}
    sig = P7.build_sig_gate_b(rows, cal_ext, closes, op, start=SIG_START, signal="B")
    return sig if len(sig) else pd.DataFrame(columns=cols)


def _opens_known(sids, markets: pd.Series, cal: pd.DatetimeIndex, n_ext: int, asof_pos: int) -> dict:
    """真開盤價到 asof 為止；asof 之後一律 1（＝ 還不知道，⛔ 不當剔除理由，也 ⛔ 不偷看）。"""
    out = {}
    for s in sids:
        o = np.ones(n_ext)
        st = D.load_stock(s, markets[s], cal)
        if st is not None:
            o[:asof_pos + 1] = st.df["open"].to_numpy(float)[:asof_pos + 1]
        out[s] = o
    return out


def _tf(x) -> str:
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "NaN"
    return "T" if bool(x) else "F"


def _num(x) -> str:
    return "NaN" if x is None or pd.isna(x) else f"{float(x):.0f}"


def gate_b_status(sids, asof, window: int = WINDOW) -> tuple[pd.DataFrame, pd.DataFrame]:
    """回 (逐檔表, 觸發事件表)。逐檔表一檔一列（順序同 sids）；事件表列出量測日落在 [asof_pos − window, asof_pos] 的每一次觸發。"""
    sids = [str(s).strip() for s in sids]
    cal = D.load_calendar()
    asof_pos = int(cal.searchsorted(pd.Timestamp(asof), side="right")) - 1
    if asof_pos < 0:
        raise ValueError(f"asof {asof} 早於日曆起點 {cal[0].date()}")
    lo = max(0, asof_pos - window)                         # ⭐ 多取一天：L2 的第二種讀法要用
    positions = P.measurement_days(cal, str(cal[lo].date()), str(cal[asof_pos].date()))
    if len(positions) == 0 or cal[positions[0]] < pd.Timestamp(SIG_START):
        raise ValueError(f"asof {asof} 太早：窗內量測日要在 {SIG_START} 之後（build_sig_gate_b 的起點）")
    last_mpos = int(positions[-1])
    stocks, U = load_gate3()
    in_g = set(U["stock_id"])
    ok = [s for s in sids if s in in_g]
    rows = panel_rows(ok, cal, positions, U) if ok else pd.DataFrame(columns=["stock_id", "measure_date"])
    fut, fut_basis = future_trading_days(cal, 2 * window + 10)
    cal_ext = cal.append(fut)
    sig = signal_rows(rows, cal_ext)                                                  # 純訊號（L1）
    markets = U.set_index("stock_id")["market"]
    kept = signal_rows(rows, cal_ext, _opens_known(ok, markets, cal, len(cal_ext), asof_pos))   # 真開盤價下 build_sig_gate_b 留不留
    kept_keys = set(zip(kept["sid"], kept["month"]))

    def basis_of(p: int) -> str:
        return "資料日曆" if p < len(cal) else fut_basis[p - len(cal)]

    ev = pd.DataFrame()
    if len(sig):
        r = rows[["stock_id", "measure_date"]].copy()
        r["month"] = r["measure_date"].dt.strftime("%Y-%m")
        ev = r.merge(sig[["sid", "month", "entry_pos", XCOL]].rename(columns={"sid": "stock_id"}), on=["stock_id", "month"], how="inner",
                     validate="one_to_one")
        ev["measure_pos"] = cal.get_indexer(ev["measure_date"])
        assert (ev["entry_pos"] == ev["measure_pos"] + 1).all(), "entry_pos 應 ＝ 量測日次一交易日"
        ev["in_window_120"] = ev["measure_pos"] >= asof_pos - window + 1
        ev["holding_on_asof"] = (ev["entry_pos"] <= asof_pos) & (asof_pos <= ev[XCOL])
        ev["day_n"] = np.where(ev["entry_pos"] <= asof_pos, asof_pos - ev["entry_pos"] + 1, 0)
        ev["entry_date"] = [cal_ext[int(p)] for p in ev["entry_pos"]]
        ev["exit_date"] = [cal_ext[int(p)] for p in ev[XCOL]]
        ev["exit_date_basis"] = [basis_of(int(p)) for p in ev[XCOL]]
        ev["entry_open_ok"] = ["未到" if e > asof_pos else ("T" if (s, m) in kept_keys else "F")
                               for s, m, e in zip(ev["stock_id"], ev["month"], ev["entry_pos"])]
        ev = ev.sort_values(["stock_id", "measure_date"]).reset_index(drop=True)
    meta = stocks.drop_duplicates("stock_id").set_index("stock_id")
    out = []
    for s in sids:
        row = {"stock_id": s, "name": meta["name"].get(s, ""), "market": meta["market"].get(s, ""),
               "asof": str(cal[asof_pos].date()), "data_last_day": str(cal[-1].date()), "measure_date": str(cal[last_mpos].date())}
        if s not in in_g:
            out.append({**row, "status": f"{NOT_IN}（{why_not_in_universe(s, stocks)}）"})
            continue
        m = rows[(rows["stock_id"] == s) & (rows["measure_date"] == cal[last_mpos])]
        if m.empty:
            row["status"] = "量測日無成交或不在籍 ⇒ 本月無判定（L5）"
        else:
            m = m.iloc[0]
            row.update(status="已判定", liq_ok=_tf(m["liq_ok"]), bars_ok=_tf(m["bars_ok"]), inst_ok=_tf(m["inst_ok"]),
                       eligible=_tf(m["eligible"]), rev_hi24=_num(m["rev_hi24"]), ma60_up=_num(m["ma60_up"]),
                       ma_stack=_num(m["ma_stack"]), amt20=m["amt20"], bars=int(m["bars"]))
            row["signal"] = "T" if (s, cal[last_mpos].strftime("%Y-%m")) in set(zip(sig["sid"], sig["month"])) else "F"
        e = ev[(ev["stock_id"] == s) & ev["in_window_120"]] if len(ev) else pd.DataFrame()
        row["n_trig_120d"] = int(len(e))
        row["trig_measure_dates"] = ";".join(str(d.date()) for d in e["measure_date"]) if len(e) else ""
        if len(e):
            t = e.iloc[-1]
            row.update(last_trig_measure_date=str(t["measure_date"].date()), last_trig_entry_date=str(t["entry_date"].date()),
                       last_trig_day_n=int(t["day_n"]), last_trig_exit_date=str(t["exit_date"].date()),
                       last_trig_exit_basis=t["exit_date_basis"], last_trig_entry_open_ok=t["entry_open_ok"])
        out.append(row)
    cols = ["stock_id", "name", "market", "status", "asof", "data_last_day", "measure_date", "liq_ok", "bars_ok", "inst_ok", "eligible",
            "rev_hi24", "ma60_up", "ma_stack", "signal", "amt20", "bars", "n_trig_120d", "trig_measure_dates", "last_trig_measure_date",
            "last_trig_entry_date", "last_trig_day_n", "last_trig_exit_date", "last_trig_exit_basis", "last_trig_entry_open_ok"]
    tab = pd.DataFrame(out).reindex(columns=cols)
    for c in ("bars", "n_trig_120d", "last_trig_day_n"):
        tab[c] = tab[c].astype("Int64")
    ev_cols = ["stock_id", "measure_date", "entry_date", "entry_pos", "day_n", XCOL, "exit_date", "exit_date_basis",
               "in_window_120", "holding_on_asof", "entry_open_ok"]
    ev = ev.reindex(columns=ev_cols) if len(ev) else pd.DataFrame(columns=ev_cols)
    return tab, ev


COL_DOC = [
    ("stock_id／name／market", "代號／名稱／市場（meta/stocks.csv）"),
    ("status", f"已判定｜{NOT_IN}（原因：興櫃、非上市櫃普通股、-DR、創新板、查無代號；判定一律由 gate3 決定）｜量測日無成交或不在籍 ⇒ 本月無判定"),
    ("asof／data_last_day", "實際採用的判定日（≤ 指定 asof 的最後一個交易日）／資料快照的最後交易日"),
    ("measure_date", "asof 以前最後一個量測日（每月第一個交易日）——下面九欄全是這一天的值"),
    ("liq_ok", "流動性閘：近 20 日均成交額 amt20 ≥ 5,000 萬元（T/F）"),
    ("bars_ok", "根數閘：量測日有價收盤根數 bars ≥ 120（T/F）"),
    ("inst_ok", "法人閘：外資與投信近 20 日淨買超都可算（窗內無缺值）（T/F）"),
    ("eligible", "三閘都 T 才是 T（＝ liq_ok ∧ bars_ok ∧ inst_ok）"),
    ("rev_hi24", "100＝可得的最新一期月營收 ≥ 前 24 期最高（對稱容差 1e-4）；0＝否；NaN＝不明（覆蓋不足／存託憑證）"),
    ("ma60_up", "100＝MA60 今日 > 20 個交易日前的 MA60；0＝否"),
    ("ma_stack", "100＝close > MA20 > MA60 > MA120（多頭排列）；0＝否。⭐ 門檻B 要的是 0"),
    ("signal", "門檻B 訊號（T/F）＝ eligible ∧ rev_hi24＝100 ∧ ma60_up＝100 ∧ ma_stack＝0（researchp7.build_sig_gate_b 的輸出）"),
    ("amt20／bars", "參考：近 20 日均成交額（元）／有價收盤根數"),
    ("n_trig_120d／trig_measure_dates", "最近 120 個交易日內（asof 當日算第 1 個）觸發的次數／各次的量測日"),
    ("last_trig_measure_date", "最近一次觸發的量測日"),
    ("last_trig_entry_date", "進場日＝該量測日的次一交易日（開盤進）"),
    ("last_trig_day_n", "asof 是持有期的第幾個交易日（進場日＝第 1 個；0＝尚未進場）"),
    ("last_trig_exit_date", "預計出場日＝持有第 120 個交易日（收盤出）"),
    ("last_trig_exit_basis", "出場日的依據：資料日曆｜休市表外推｜只扣週末（該年休市表未公告 ⇒ 元旦、春節等休市沒扣，實際出場日只會更晚）；三者都不含颱風等臨時休市"),
    ("last_trig_entry_open_ok", "進場日有沒有開盤價（T/F；未到＝進場日在 asof 之後）。F ⇒ 回測（build_sig_gate_b）會剔除這一筆"),
]


def _md_table(df: pd.DataFrame) -> str:
    def cell(v):
        if v is None or (not isinstance(v, str) and pd.isna(v)):
            return ""
        if isinstance(v, pd.Timestamp):
            return str(v.date())
        if isinstance(v, float):
            return f"{v:,.0f}"
        return str(v)
    L = ["| " + " | ".join(df.columns) + " |", "|" + "---|" * len(df.columns)]
    L += ["| " + " | ".join(cell(v) for v in r) + " |" for r in df.itertuples(index=False)]
    return "\n".join(L)


def write_outputs(tab: pd.DataFrame, ev: pd.DataFrame, out: str) -> list[str]:
    os.makedirs(out, exist_ok=True)
    tag = tab["asof"].iloc[0].replace("-", "")
    p_tab = os.path.join(out, f"gate_b_status_{tag}.csv")
    p_ev = os.path.join(out, f"gate_b_events_{tag}.csv")
    p_md = os.path.join(out, f"gate_b_status_{tag}.md")
    tab.to_csv(p_tab, index=False)
    ev.to_csv(p_ev, index=False)
    L = [f"# 門檻B 逐檔判定（asof {tab['asof'].iloc[0]}）", "",
         f"資料：main `{H2.SHA}`（最後交易日 {tab['data_last_day'].iloc[0]}）；母體 gate3；程式 `backtest/gate_b_status.py`。", "",
         "## 附註", ""] + [f"- {n}" for n in NOTES] + ["",
         "## 逐欄說明（`" + os.path.basename(p_tab) + "`）", "", "| 欄 | 意思 |", "|---|---|"] + \
        [f"| {k} | {v} |" for k, v in COL_DOC] + ["",
         f"事件表 `{os.path.basename(p_ev)}`：量測日落在 [asof − {WINDOW} 個交易日, asof] 的每一次觸發（多列一天給第二種讀法）；"
         "`in_window_120`＝落在最近 120 個交易日內（asof 當日算第 1 個）、`holding_on_asof`＝asof 當日仍在持有期內。", "",
         "## 表", "", _md_table(tab.drop(columns=["data_last_day"])), "", "## 事件", "", _md_table(ev), ""]
    open(p_md, "w", encoding="utf-8").write("\n".join(L) + "\n")
    return [p_tab, p_ev, p_md]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--asof", default=None, help="預設＝資料最後交易日")
    ap.add_argument("--sids", default=",".join(TRACK))
    ap.add_argument("--out", default=OUT)
    a = ap.parse_args()
    asof = a.asof or str(D.load_calendar()[-1].date())
    tab, ev = gate_b_status(a.sids.split(","), asof)
    with pd.option_context("display.width", 250, "display.max_columns", 40):
        print(tab.to_string(index=False))
        print(ev.to_string(index=False))
    for p in write_outputs(tab, ev, a.out):
        print("寫出", p)


if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
"""短期狀態標籤（台股策略線 起草全文 seq2 §一，sha f41e5f4420657e84；裁定線 seq152 已過目）——回測線落地，交情報線呼叫。

⭐ 性質：描述規則，⛔ 不是預測、⛔ 不是賣出條件、⛔ 不計 N。

用法：
    from backtest.state_label import state_label, state_label_batch
    state_label("2609", "2026-09-24")                 # dict
    state_label_batch(["2609", "6209"], "2026-09-24")  # DataFrame（一檔一列）
  命令列：python backtest/state_label.py 2609 6209 … [--asof YYYY-MM-DD]（不給 asof ＝ 快照最後一個交易日）

資料：main edc6f8002f 快照（~/h2data/<sha>/data，經 researchH2 把 D.DATA 指過去）；日線讀法與 researchD5 同一套：
    D.load_stock（還原價 ＝ 原始價 × F(d)，F ＝ 事件日嚴格大於 d 的因子連乘）⇒ 有效 K 棒 ＝ 還原 close 非缺（零價已視為缺）
    ⇒ MA、擺動點、「t−1」一律在【該股自己的有效 K 棒序列】上數（researchH2 R1 的慣例）。

規則（§一 逐字要點）：
  第零步 閘門：處置、注意、興櫃、硬斷點、有效 K 棒不足 80 根 ⇒「無法判定」
  ① 均線結構：MA20（還原收盤）；上揚 ＝ MA20(t) > MA20(t−1)
       A 價在 MA20 上＋上揚｜B 價站上 MA20＋下彎｜C 價在 MA20 下＋上揚｜D 價在 MA20 下＋下彎
  ② 高低點結構：擺動點 ＝ stop_fractal.swing_lows（高點用 −還原 high），k＝5、右 5 根走完才確認
       取最近兩個已確認擺動高點、兩個已確認擺動低點：上升 ＝ HH ∧ HL｜下降 ＝ LH ∧ LL｜其餘 ＝ 混合（相等 ⇒ 混合）
  ③ 標籤：偏漲 ＝ A ∧ 上升｜偏跌 ＝ D ∧ 下降｜盤整 ＝ 其餘（附結構與高低點）
  ④ 確認價 ＝ 最近一個已確認擺動高點的還原 high；破壞價 ＝ 最近一個已確認擺動低點的還原 low；兩點之間有除權息 ⇒ 附「已含除權息調整」

⭐ 落地讀法（規則沒寫死、本線選一種；交件逐條列出，⛔ 沒有改規則）：
 L1 「價在 MA20 上」＝ 還原 close(t) > MA20(t)（嚴格）；close ＝ MA20 算「下」。「站上」與「在上」同一個判準（B 與 A 只差均線方向）。
    「下彎」＝ 非上揚（MA20(t) ≤ MA20(t−1)；持平算下彎——規則只定義了上揚，其餘全歸下彎）。
 L2 「右 5 根走完」數的是【有效 K 棒】（與 MA 同一條序列）；實作上把序列截在 asof（含）再呼叫 swing_lows ⇒
    swing_lows 只對 s ≤ n−1−k 判定 ⇒ 用到的擺動點一定滿足 s＋5 ≤ asof 的位置 ⇒ ⛔ 結構上不可能前視（fixture ⑤⑥ 驗）。
    swing_lows 是【嚴格】不等式 ⇒ 平頂／平底（相鄰同價）不成為擺動點（沿用函式原樣，⛔ 不改共用碼）。
 L3 已確認擺動高點或低點不足兩個 ⇒ 高低點結構 ＝「混合」（規則「其餘 ＝ 混合」的字面），另在 note 寫「擺動點不足」。
    不足一個 ⇒ 確認價／破壞價為 NaN。
 L4 「兩點之間有除權息」讀成：該價位的擺動點日期 與 asof 之間（(擺動日, asof]）有 data/adj 事件
    ⇒ 還原值 ≠ 當時的原始價 ⇒ 附「已含除權息調整」。確認價、破壞價各自判一次。（另一種讀法「兩個擺動點之間」見交件。）
    data/adj 的事件含除息、除權、減資、面額變更 ⇒ 一律算（kind 欄原樣附上）。
 L5 價位尺度：輸出的還原值再除以 F(asof) ⇒ asof 那一根的因子＝1、與 asof 收盤同尺度（規則「最新日因子＝1」的一般化；
    asof ＝ 快照最後一日時 F(asof) 通常就是 1，程式照樣除並印出 F(asof)）。另附擺動點當天的【原始價】僅供對照。
 L6 閘門（資料找得到的全用；⛔ 沒有自創替代）：
    興櫃   data/meta/stocks.csv 的 market == 'emerging'（⚠ 辨識欄只有 market；kind 對興櫃也是 stock）；代號不在檔內 ⇒ 無法判定
    處置   asof 落在 data/meta/disposal.csv（sec_kind＝普通股）任一 [start_date, end_date]（含兩端）；⛔ 不加「出關後 5 日」
    注意   asof 當天出現在 data/meta/attention.csv（sec_kind＝普通股）；⛔ 不回看 N 日（另附「最近一次注意日」供參考）
    硬斷點 data.breakpoints（價格 ≤0.55／≥1.8、或連續 ≥5 個交易日無有效 K 棒，且 (前一根, 這一根] 無 adj 事件）
           ⭐ 兩條規則都算、⛔ 不帶 500 張流動性前提（同 researchH2 R3 與 tw-technical-analysis「硬斷點」字面）；
           範圍 ＝ 復牌那根落在 [min(asof−365 日曆日, 本次判讀用到的最早一根), asof]（最近一年 ＋ 判讀實際跨過的區段）
    樣本   asof（含）以前的有效 K 棒總數 < 80 ⇒ 無法判定（讀成「整條序列」的根數，⛔ 不是「最近 80 個交易日都要有成交」）
    ⚠ 閘門命中仍照算①～④並回傳（欄位供除錯），但 label ＝「無法判定」；情報線只抄 label 與 gate_reason。
 L7 asof 當天該股沒有有效 K 棒（停牌）⇒ 以 asof 以前最後一根有效 K 棒判讀，last_bar_date 標出來（不另設閘門，規則沒有這一條）。
"""
from __future__ import annotations
import os, sys, bisect
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
sys.path.insert(0, os.path.expanduser("~/tw-p17"))
import researchH2 as H2                                  # ⭐ 把 backtest.data.DATA 指到釘住的快照
D = H2.D
from backtest import stop_fractal as SF                  # ⛔ 只 import，不改

K_SWING, MA_N, MIN_BARS, BP_LOOKBACK_DAYS = 5, 20, 80, 365
STRUCT_DESC = {"A": "價在 MA20 上且 MA20 上揚：最強", "B": "價站上 MA20 但 MA20 下彎：剛轉，未確認",
               "C": "價在 MA20 下但 MA20 上揚：回檔中，趨勢未壞", "D": "價在 MA20 下且 MA20 下彎：最弱"}


# ───────────────────────── 純函式核心（fixture 直接驗這一層） ─────────────────────────
def core(h: np.ndarray, l: np.ndarray, c: np.ndarray, k: int = K_SWING, ma_n: int = MA_N) -> dict:
    """輸入：【已截在 asof（含）】的有效 K 棒還原 high／low／close（同長）。最後一根 ＝ asof 那根。
    回傳①～③與擺動點索引；⛔ 不讀任何 asof 之後的資料（呼叫端負責截斷）。"""
    n = len(c)
    out = {"n_bars": n}
    if n >= ma_n + 1:
        ma_t = float(np.mean(c[n - ma_n:])); ma_p = float(np.mean(c[n - 1 - ma_n:n - 1]))
        above = bool(c[-1] > ma_t); up = bool(ma_t > ma_p)
        st = ("A" if up else "B") if above else ("C" if up else "D")
    else:
        ma_t = ma_p = np.nan; above = up = None; st = None
    out.update(close=float(c[-1]) if n else np.nan, ma20=ma_t, ma20_prev=ma_p, above=above, ma_up=up, ma_struct=st)
    hi_idx = np.flatnonzero(SF.swing_lows(-h, k)) if n else np.array([], int)
    lo_idx = np.flatnonzero(SF.swing_lows(l, k)) if n else np.array([], int)
    out["swing_hi_idx"] = hi_idx[-2:].tolist(); out["swing_lo_idx"] = lo_idx[-2:].tolist()
    note = []
    if len(hi_idx) >= 2 and len(lo_idx) >= 2:
        h1, h2 = h[hi_idx[-2]], h[hi_idx[-1]]; l1, l2 = l[lo_idx[-2]], l[lo_idx[-1]]
        hh, lh, hl, ll = h2 > h1, h2 < h1, l2 > l1, l2 < l1
        hl_struct = "上升" if (hh and hl) else ("下降" if (lh and ll) else "混合")
        if h2 == h1 or l2 == l1:
            note.append("兩高點或兩低點相等 ⇒ 混合")
        out.update(hi_cmp="HH" if hh else ("LH" if lh else "EH"), lo_cmp="HL" if hl else ("LL" if ll else "EL"))
    else:
        hl_struct = "混合"; note.append("已確認擺動點不足兩個（高 {}／低 {}）⇒ 混合".format(len(hi_idx), len(lo_idx)))
        out.update(hi_cmp=None, lo_cmp=None)
    out["hl_struct"] = hl_struct
    out["confirm_idx"] = int(hi_idx[-1]) if len(hi_idx) else None
    out["break_idx"] = int(lo_idx[-1]) if len(lo_idx) else None
    out["confirm_adj"] = float(h[hi_idx[-1]]) if len(hi_idx) else np.nan
    out["break_adj"] = float(l[lo_idx[-1]]) if len(lo_idx) else np.nan
    if st == "A" and hl_struct == "上升":
        lab = "偏漲"
    elif st == "D" and hl_struct == "下降":
        lab = "偏跌"
    else:
        lab = "盤整"
    out["label_raw"] = lab
    out["note"] = "；".join(note)
    return out


def label_text(r: dict) -> str:
    if r.get("gate_reason"):
        return "無法判定（{}）".format(r["gate_reason"])
    if r["label_raw"] == "盤整":
        return "盤整（{}：{}；高低點{}）".format(r["ma_struct"], STRUCT_DESC[r["ma_struct"]].split("：")[1], r["hl_struct"])
    return r["label_raw"]


# ───────────────────────── 資料層 ─────────────────────────
class Ctx:
    """一次載入的中介資料（批次時共用）。"""
    def __init__(self):
        self.cal = D.load_calendar()
        m = pd.read_csv(os.path.join(D.DATA, "meta", "stocks.csv"), dtype=str)
        self.market = dict(zip(m["stock_id"], m["market"])); self.name = dict(zip(m["stock_id"], m["name"]))
        self.disp = D.load_disposal_intervals()
        self.attn = D.load_attention_dates()
        dd = pd.read_csv(os.path.join(D.DATA, "meta", "disposal.csv"), dtype=str)
        aa = pd.read_csv(os.path.join(D.DATA, "meta", "attention.csv"), dtype=str, usecols=["date"])
        self.disp_max = pd.Timestamp(dd["start_date"].max()); self.attn_max = pd.Timestamp(aa["date"].max())


_CTX: Ctx | None = None


def ctx() -> Ctx:
    global _CTX
    if _CTX is None:
        _CTX = Ctx()
    return _CTX


def state_label(sid: str, asof_date=None, C: Ctx | None = None) -> dict:
    """單檔。asof_date 省略 ＝ 快照交易日曆最後一天。回傳 dict（label 為情報線照抄的那一句）。"""
    C = C or ctx(); cal = C.cal
    asof = pd.Timestamp(asof_date) if asof_date is not None else cal[-1]
    sid = str(sid)
    r = {"sid": sid, "name": C.name.get(sid, ""), "asof": asof.date().isoformat(), "market": C.market.get(sid), "gate_reason": ""}
    gates = []
    mk = C.market.get(sid)
    if mk is None:
        r["gate_reason"] = "代號不在 stocks.csv"; r["label"] = label_text(r); return r
    if mk == "emerging":
        gates.append("興櫃")
    st = D.load_stock(sid, mk, cal) if mk != "emerging" else None
    if st is None:
        gates.append("無日線" if mk != "emerging" else "")
        r["gate_reason"] = "、".join(g for g in gates if g); r["label"] = label_text(r); return r
    ia = int(cal.searchsorted(asof, side="right")) - 1          # asof（含）以前最後一個日曆位置
    df = st.df
    cfull = df["close"].to_numpy(float)
    vpos = np.flatnonzero(np.isfinite(cfull[:ia + 1]))          # asof（含）以前的有效 K 棒（日曆位置）
    F = D.cum_factor_series(cal, D.load_adj(sid))
    h = df["high"].to_numpy(float)[vpos]; l = df["low"].to_numpy(float)[vpos]; c = cfull[vpos]
    res = core(h, l, c)
    r.update({k_: v for k_, v in res.items() if k_ not in ("swing_hi_idx", "swing_lo_idx")})
    if len(vpos):
        f_asof = float(F[vpos[-1]]); r["last_bar_date"] = cal[vpos[-1]].date().isoformat(); r["F_asof"] = f_asof
        r["close"] = res["close"] / f_asof; r["ma20"] = res["ma20"] / f_asof; r["ma20_prev"] = res["ma20_prev"] / f_asof
        ev = sorted(pd.Timestamp(x) for x in st.event_dates)
        adj = D.load_adj(sid)
        kind_of = dict(zip(adj["date"], adj["kind"])) if adj is not None and "kind" in adj else {}
        for key, idx, col in (("confirm", res["confirm_idx"], "high"), ("break", res["break_idx"], "low")):
            if idx is None:
                r[key + "_price"] = np.nan; r[key + "_date"] = None; r[key + "_exdiv"] = None; continue
            p = int(vpos[idx]); d0, d1 = cal[p], cal[vpos[-1]]
            r[key + "_price"] = res[key + "_adj"] / f_asof
            r[key + "_raw"] = res[key + "_adj"] / float(F[p])                      # 擺動點當天的原始價（僅對照）
            r[key + "_date"] = d0.date().isoformat()
            evs = [e for e in ev if d0 < e <= d1]
            r[key + "_exdiv"] = bool(evs)
            r[key + "_events"] = ",".join("{}{}".format(e.date(), kind_of.get(e, "")) for e in evs)
        r["swing_hi_dates"] = ",".join(cal[vpos[i]].date().isoformat() for i in res["swing_hi_idx"])
        r["swing_lo_dates"] = ",".join(cal[vpos[i]].date().isoformat() for i in res["swing_lo_idx"])
        r["swing_hi_vals"] = ",".join("{:.4f}".format(h[i] / f_asof) for i in res["swing_hi_idx"])
        r["swing_lo_vals"] = ",".join("{:.4f}".format(l[i] / f_asof) for i in res["swing_lo_idx"])
    # 閘門
    if res["n_bars"] < MIN_BARS:
        gates.append("有效 K 棒不足 80 根（{}）".format(res["n_bars"]))
    if asof > C.disp_max or asof > C.attn_max:
        gates.append("處置／注意資料未涵蓋 asof")
    if any(s <= asof <= e for s, e in C.disp.get(sid, [])):
        gates.append("處置")
    ad = C.attn.get(sid, set())
    if asof in ad:
        gates.append("注意")
    past = [d for d in ad if d <= asof]
    r["last_attention"] = max(past).date().isoformat() if past else None
    used = [i for i in res["swing_hi_idx"] + res["swing_lo_idx"]] + ([len(vpos) - 1 - MA_N] if len(vpos) > MA_N else [0])
    first_used = int(vpos[max(0, min(used))]) if len(vpos) else ia
    lo = min(int(cal.searchsorted(asof - pd.Timedelta(days=BP_LOOKBACK_DAYS))), first_used)
    bps = [b for b in D.breakpoints(df.iloc[:ia + 1], st.event_dates) if lo <= b["pos"] <= ia]
    if bps:
        gates.append("硬斷點（{}）".format("、".join("{} {}".format(cal[b["pos"]].date(), b["rule"]) for b in bps)))
    r["bp_scan_from"] = cal[lo].date().isoformat()
    r["gate_reason"] = "、".join(gates)
    r["label"] = label_text(r) if res.get("ma_struct") or r["gate_reason"] else "無法判定（均線算不出）"
    r["confirm_text"] = None if not np.isfinite(r.get("confirm_price", np.nan)) else \
        "收盤站上 {:.2f} ＝ 越過最近擺動高點{}".format(r["confirm_price"], "（已含除權息調整）" if r.get("confirm_exdiv") else "")
    r["break_text"] = None if not np.isfinite(r.get("break_price", np.nan)) else \
        "收盤跌破 {:.2f} ＝ 跌破最近擺動低點{}".format(r["break_price"], "（已含除權息調整）" if r.get("break_exdiv") else "")
    return r


def state_label_batch(sids, asof_date=None) -> pd.DataFrame:
    C = ctx()
    return pd.DataFrame([state_label(s, asof_date, C) for s in sids])


COLS = ["sid", "name", "asof", "last_bar_date", "label", "gate_reason", "ma_struct", "hl_struct", "hi_cmp", "lo_cmp",
        "close", "ma20", "ma20_prev", "confirm_price", "confirm_date", "confirm_exdiv", "confirm_raw", "break_price", "break_date",
        "break_exdiv", "break_raw", "swing_hi_dates", "swing_hi_vals", "swing_lo_dates", "swing_lo_vals", "n_bars", "F_asof",
        "last_attention", "bp_scan_from", "confirm_events", "break_events", "note", "confirm_text", "break_text"]

if __name__ == "__main__":
    args = [a for a in sys.argv[1:]]
    asof = None
    if "--asof" in args:
        i = args.index("--asof"); asof = args[i + 1]; del args[i:i + 2]
    out = state_label_batch(args or ["2609", "6209", "3535", "4164", "6282", "6443", "8289", "6469"], asof)
    os.makedirs("backtest/resultsSR", exist_ok=True)
    p = "backtest/resultsSR/state_label_demo.csv"
    out.reindex(columns=COLS).to_csv(p, index=False, encoding="utf-8")
    pd.set_option("display.width", 250); pd.set_option("display.max_columns", 50)
    print(out.reindex(columns=COLS).to_string())
    print("快照", H2.SHA, "｜處置資料至", ctx().disp_max.date(), "｜注意資料至", ctx().attn_max.date(), "｜寫出", p)

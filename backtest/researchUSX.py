# -*- coding: utf-8 -*-
"""USREG-X（美股移植 PREREGX：型態量幅目標達成率＋成形前讀法）——pre（頻率、可判定性算術）＋本體。

    PYTHONPATH=$HOME/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchUSX --pre  [--procs 2]   # 只報頻率與算術（⛔ 不算任何報酬／達成）
    PYTHONPATH=$HOME/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchUSX --main [--procs 2]   # 本體

判準：美股登錄 seq2（a3c98a07e882a574，正文）＋seq3（81bfc48eff6258f5）＋seq4（cbfc7610923b9e53）＋seq5（ffb22ecb1bd749ff）；
     移植來源 台股 PREREGX seq2（7de459d6a4578cf6）；裁定 seq163 §四②、seq168 §二（甲只判 H60、H120 依構造不可判定改描述、
     H60 結論句上限「樣本中等」、⛔ 不切小區段）；回測線 1819 開跑前算術。
讀法：裁定 seq214 §三（R1～R4、B1～B7；USREG-M 本體 5c30bcec6b 的 B1 斷點規則）＋台股 researchX Y1～Y11、patterns_x X1～X11 照先例。
偵測器：backtest/patterns_x.py（台股同一支，⛔ 未改）；T1：selftest_patterns_x.run_all()（台股）＋本支 usx_fixtures()（美股資料型態）。

⛔⛔ 授權：resultsUSX/ 只寫彙總；逐筆事件、逐檔數字寫 ~/us_work/usx/（repo 外）並列 sha。

⭐ 讀法（★ ＝ 台股先例有兩種讀法、此處照先例；登錄沒寫、改動事件集合或出口的新讀法 ⇒ 先停下來回報）：
 V1 價格、日曆、母體、暖身、無效 K 棒 ＝ USREG-M 同一套（us_data scope＝panel、NYSE 日曆、T／S 當天 in_index＝1 且有有效 K 棒、R1 不在母體 ⇒ 不是事件、不開合併窗）。
 V2 成交量（研究二箱型的 3 倍量、杯柄的柄量縮與 1.4 倍量要用）：同一個 src 檔的同日列；Yahoo ＝ volume 欄（Yahoo 已按拆股調整）、
    Tiingo ＝ adjVolume（拆股調整，與還原價同一把尺）。〔Tiingo 原始 volume 版的事件差另報〕無效 K 棒那天量也當缺。
 V3 研究二 Frame 的 event_dates（台股 ＝ 除權息日，訊號日不可是事件日）⇒ 美股 ＝ 轉接層 hard_break 日（seam／split_div）；
    這些日子本來就在 V4 的型態視窗斷點裡 ⇒ 不改保留集合。Frame.gate 全開（台股同，母體另判）。
 V4 硬斷點（R2＝P0、R3＝S1）：型態視窗 [第一轉折, T]（台股 Y3）、未來窗 甲 (T, T+120]／乙 (S, S+40]（台股 Y4）內
    有轉接層 hard_break 或任一天沒有有效 K 棒（只數該股第一根～最後一根有效 K 棒之間；最後一根之後＝下市，同 USREG-M）⇒ 剔除。
    ⚠ 台股 Y3 的「處置、注意」美股沒有 ⇒ 拿掉（seq1 §一：處置／注意 ⛔ 全部拿掉）。
 V5 T+1（乙 S+1）沒有有效 K 棒 ⇒ 剔除；台股的「T+1 開盤漲停」拿掉。
 V6 ★ 甲的事件窗：T ≤ 窗尾−120，H60 與 H120 用同一批事件（台股 Y1 先例）〔另一讀法 T ≤ 窗尾−60 的件數另報〕；乙 S ≤ 窗尾−40。
 V7 甲 判定：只以 H60 下結果（seq3 §二）；H120 ＝ 描述、逐字標「依構造不可判定」；n_eff ＝ min(事件數, 以窗首切的 60 日區段數)；
    出口①：n_eff ＜ 30 或 事件達成數 ＜ 30 或 對照達成數 ＜ 30（台股 Y8／researchH2.judge）；H60 依構造最多 43 段 ⇒ 最好出口②，
    結論句前加「樣本中等（n_eff＝n，介於 30 與 100 之間）：」。⛔ 不切小區段。
 V8 對照（seq1 §二 X）：同 T 日、20 日波動同十分位（十分位在 T 日【in_index 且波動可算】的母體內算，平手依代號）、
    T 日沒有本件五型任何原始觸發、不是事件股、對照也通過 V4 未來窗（120 日）與 V5 ⇒ 每型一條亂數流 default_rng(20260925)，
    事件依 (T, 代號) 排序逐筆抽 1 檔；H60、H120 同一檔。池空 ⇒ 剔除計數。
 V9 乙 判定量 X ＝ close(≤ S+20 最後一根)／open(S+1) − 1 − 0.05% − EW20(S+1)（台股 Y9 形狀）；
    EW20(d) ＝ d 日 in_index、有效 K 棒、開盤 > 0 的股票 close(≤ d+19 最後一根)／open(d) − 1 等權（B1；(d, d+19] 有 hard_break 者不進）。
    20 日區段（窗首起，S ≤ 窗尾−40 ⇒ 最多 132 段）。成形／破壞／都沒發生照台股 Y9、X8。
 V10 假訊號臂（seq4，B4 照 USREG-M）：每檔抽數 ＝ 該檔該格保留真事件數；可抽日 ＝ 窗內、in_index、有有效 K 棒、通過同一套未來窗與 T+1 規則
    （甲 另需波動可算）；新預設 ＝ 排除「存在該格保留真事件 T_r ∈ [t−20, t]」的日子；不放回、不合併、不補抽；
    甲 的假日子依序配該檔真事件（依 T 排序）的目標距離％，再照 V8 抽對照 ⇒ D_A(60)；乙 ⇒ X。
    版本：新預設（判準警語用）、不排除（描述）、同檔同月（台股原登錄，描述；seq4 §一）。
    種子 default_rng([20260925＋r, crc32(代號), 型序號, 版本序號])；r＝0…29；判過 ＝ CI（月分群）不含 0。
 V11 頻率：每檔每年 ＝ 保留數 ÷（該檔在 [窗首, 甲 窗尾−120／乙 窗尾−40] 內 in_index 且有 K 棒的日數 ÷ 每年交易日數）；另報台股 Y11 跨距式。
 V12 研究二對帳（台股 6,417／116、60%／41%）只適用台股資料 ⇒ 美股不做；杯柄的 Bulkowski 76%／50% 只並列。
"""
from __future__ import annotations
import os, sys, time, json, io, csv, zlib, hashlib
from collections import Counter
from multiprocessing import Pool
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17"))
sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
from backtest import us_data as U
from backtest import patterns_x as PX
from backtest import researchUSM as RU
from backtest import researchUSM_body as MB
from backtest import research11 as R11

OUT = os.path.expanduser("~/tw-p17/backtest/resultsUSX")
WORK = os.path.expanduser("~/us_work/usx")
HOR = (60, 120); HMAX = 120; HJ = 60
FORM_N, EX_N, MERGE = 40, 20, 20
SEED, FAKE_R = 20260925, 30
COST = U.COST_ROUNDTRIP
TA, TB = PX.TYPES_A, PX.TYPES_B
NAME = {"box": "箱型", "cup": "杯柄", "w": "W 底", "hs": "頭肩底", "flag": "旗形", "trend": "趨勢線"}
FVERS = ("新預設_只排除過去20日", "不排除（描述）", "同檔同月（描述）")
_G = {}


def _cnt(cs, a, b):
    b = min(b, len(cs) - 1)
    if b < a:
        return 0
    return int(cs[b] - (cs[a - 1] if a > 0 else 0))


def sha256f(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


# ═════════════ 成交量（V2）═════════════
_VC = {}


def _read_vol(src, raw_tiingo=False):
    key = (src, raw_tiingo)
    if key in _VC:
        return _VC[key]
    kind, f = src.split(":", 1)
    if kind == "yahoo":
        d = pd.read_csv(U._p("prices_yahoo", f + ".csv"), usecols=["date", "volume"], dtype={"date": str})
        v = d["volume"]
    else:
        col = "volume" if raw_tiingo else "adjVolume"
        d = pd.read_csv(U._p("prices", f + ".csv"), usecols=["date", col], dtype={"date": str})
        v = d[col]
    s = pd.Series(v.to_numpy(float), index=pd.DatetimeIndex(pd.to_datetime(d["date"])))
    _VC[key] = s
    return s


def volume_aligned(t, cal, valid, raw_tiingo=False):
    """面板每一列的 src 檔同日量 ⇒ 對齊日曆；沒有有效 K 棒的日子 ⇒ NaN。"""
    pn = U.panel(t)
    V = np.full(len(cal), np.nan)
    for src, g in pn.groupby("src", sort=False):
        s = _read_vol(src, raw_tiingo)
        idx = g.index[g.index.isin(cal)]
        v = s.reindex(idx).to_numpy(float)
        V[cal.get_indexer(idx)] = v
    V[~valid] = np.nan
    return V


# ═════════════ 讀檔＋偵測（worker）═════════════
def _init(cal, w0, w1):
    _G.update(cal=cal, w0=w0, w1=w1)


def detect_box_cup(o, h, l, c, V, valid, cal, pbdays):
    fd = pd.DataFrame({"open": o, "high": h, "low": l, "close": c, "volume": V, "traded": valid}, index=cal)
    f = PX.frame_open(fd, pbdays)
    A_box = [{"T": e["T"], "first": e["first"], "target": e["target"], "level": e["level"], "low": e["low"]} for e in PX.box_events(f)]
    bdays = np.array(sorted({e["T"] for e in A_box}), int)
    B_box = []
    for s in PX.box_forming(f):
        k = int(np.searchsorted(bdays, s["S"], side="right"))
        B_box.append({"S": s["S"], "first": s["first"], "id": s["id"], "low": s["low"],
                      "trig": int(bdays[k]) if k < len(bdays) else None, "end": None})
    ce = PX.cup_events(f)
    sig2, cg = PX.cup_scan(f)
    assert [x["signal_pos"] for x in sig2] == [x["T"] for x in ce], "⛔ cup_scan 與 patterns.cup_handle 突破清單不同"
    A_cup = [{"T": e["T"], "first": e["first"], "depth": float(e["depth_px"]), "low": float(e["low"]),
              "pts": {"L": e["L"], "B": e["B"], "R": e["R"]}} for e in ce]
    B_cup = [{"S": g["S"], "first": g["first"], "id": g["id"], "low": g["low"], "trig": g["trig"], "end": g["end"]}
             for g in cg if g["S"] is not None]
    return A_box, B_box, A_cup, B_cup


def load_one(t):
    cal, w0, w1 = _G["cal"], _G["w0"], _G["w1"]; n = len(cal)
    df = U.load_ohlc(t, scope="panel")
    if len(df) == 0:
        return None
    A0 = RU.prep(df, cal)
    if len(A0["bars"]) < 30:
        return None
    S = MB.Stk(t, A0, MB.low_aligned(df, cal), RU.member_array(t, cal), RU.span_start_array(t, cal), w0, w1 - HMAX)
    o, h, l, c, valid, bars = S.o, S.h, S.l, S.c, S.valid, S.bars
    V = volume_aligned(t, cal, valid)
    cff = pd.Series(c).ffill().to_numpy()
    ret = np.full(n, np.nan); ret[1:] = c[1:] / c[:-1] - 1.0
    vol20 = pd.Series(ret).rolling(20, min_periods=20).std(ddof=1).to_numpy()
    cb, ob, hb = c[bars], o[bars], h[bars]
    A, B = {}, {}
    for kind in ("w", "hs", "flag"):
        r = PX.detect_turn(kind, cb)
        A[kind] = [{"T": int(bars[e["T"]]), "first": int(bars[e["first"]]), "target": float(e["target"]), "level": float(e["level"]),
                    "low": float(e["low"]), "pts": {k_: int(bars[x]) for k_, x in e["pts"].items()}} for e in r["events"]]
        B[kind] = [{"S": int(bars[g["S"]]), "first": int(bars[g["first"]]), "id": tuple(int(bars[x]) for x in g["id"]),
                    "low": float(g["S_low"] if kind == "flag" else g["low"]),
                    "trig": int(bars[g["trig"]]) if g["trig"] is not None else None,
                    "end": int(bars[g["end"]]) if g["end"] is not None and g["end"] >= 0 else None}
                   for g in r["groups"] if g["S"] is not None]
    pbdays = set(cal[S.pb])
    A["box"], B["box"], A["cup"], B["cup"] = detect_box_cup(o, h, l, c, V, valid, cal, pbdays)
    alt = None
    if any(s.startswith("tiingo:") for s in U.panel(t)["src"].unique()):
        Vr = volume_aligned(t, cal, valid, raw_tiingo=True)
        ab, bb, ac, bc = detect_box_cup(o, h, l, c, Vr, valid, cal, pbdays)
        alt = {"box_T": [e["T"] for e in ab], "cup_T": [e["T"] for e in ac], "boxS": [g["S"] for g in bb], "cupS": [g["S"] for g in bc]}
    rt = PX.trend_forming(ob, hb, cb)
    B["trend"] = [{"S": int(bars[g["S"]]), "first": int(bars[g["first"]]), "id": tuple(int(bars[x]) for x in g["id"]), "low": g["low"],
                   "trig": int(bars[g["trig"]]) if g["trig"] is not None else None, "end": int(bars[g["end"]])}
                  for g in rt["groups"] if g["S"] is not None]
    return {"t": t, "S": S, "cff": cff, "vol": vol20, "A": A, "B": B, "alt": alt}


# ═════════════ 保留（台股 Y2 順序；V1、V4、V5）═════════════
def keep_A(R, typ, w0, wE, n, evs=None, hz=HMAX):
    S = R["S"]
    acc = {"原始_窗內且在母體": 0, "窗內但不在母體": 0, "合併掉": 0, "剔除_型態視窗斷點": 0, "剔除_未來窗斷點": 0,
           "剔除_T+1停牌": 0, "剔除_20日波動不可算": 0, "未來窗內下市（保留，描述）": 0}
    out = []; t_keep = -10 ** 9
    for e in sorted(R["A"][typ] if evs is None else evs, key=lambda x: x["T"]):
        T = e["T"]
        if not (w0 <= T <= wE):
            continue
        if not (S.member[T] and S.valid[T]):
            acc["窗內但不在母體"] += 1; continue
        acc["原始_窗內且在母體"] += 1
        if t_keep < T <= t_keep + MERGE:
            acc["合併掉"] += 1; continue
        if S.brk(e["first"], T):
            acc["剔除_型態視窗斷點"] += 1; continue
        if T + hz >= n or S.brk(T + 1, T + hz):
            acc["剔除_未來窗斷點"] += 1; continue
        if not S.valid[T + 1]:
            acc["剔除_T+1停牌"] += 1; continue
        if not np.isfinite(R["vol"][T]):
            acc["剔除_20日波動不可算"] += 1; continue
        e2 = dict(e)
        if typ == "cup":
            e2["target"] = float(S.o[T + 1] + e["depth"]); e2["target_half"] = float(S.o[T + 1] + 0.5 * e["depth"])
        e2["dist"] = e2["target"] / S.c[T] - 1.0
        e2["dl_in"] = S.last < T + hz
        acc["未來窗內下市（保留，描述）"] += int(e2["dl_in"])
        out.append(e2); t_keep = T
    return out, acc


def keep_B(R, typ, w0, wB, n):
    S = R["S"]
    acc = {"形成段數_有S": 0, "S_窗內且在母體": 0, "窗內但不在母體": 0, "合併掉": 0, "剔除_型態視窗斷點": 0,
           "剔除_未來窗斷點": 0, "剔除_S+1停牌": 0}
    first = {}
    for g in sorted(R["B"][typ], key=lambda x: x["S"]):
        if g["id"] not in first:
            first[g["id"]] = g
    acc["形成段數_有S"] = len(first)
    out = []; s_keep = -10 ** 9
    for g in sorted(first.values(), key=lambda x: x["S"]):
        s = g["S"]
        if not (w0 <= s <= wB):
            continue
        if not (S.member[s] and S.valid[s]):
            acc["窗內但不在母體"] += 1; continue
        acc["S_窗內且在母體"] += 1
        if s_keep < s <= s_keep + MERGE:
            acc["合併掉"] += 1; continue
        if S.brk(g["first"], s):
            acc["剔除_型態視窗斷點"] += 1; continue
        if s + FORM_N >= n or S.brk(s + 1, s + FORM_N):
            acc["剔除_未來窗斷點"] += 1; continue
        if not S.valid[s + 1]:
            acc["剔除_S+1停牌"] += 1; continue
        out.append(dict(g)); s_keep = s
    return out, acc


def load_all(procs, lim=None):
    t0 = time.time()
    calF = U.load_calendar(); cal = calF[calF >= MB.CAL0]; n = len(cal)
    w0 = int(cal.searchsorted(U.WINDOW[0])); w1 = int(cal.searchsorted(U.WINDOW[1]))
    assert cal[w0] == U.WINDOW[0] and cal[w1] == U.WINDOW[1]
    tick = [t for t in U.universe_table()["ticker"] if t not in set(U.no_ohlc_tickers())]
    if lim:
        tick = tick[:lim]
    with Pool(procs, initializer=_init, initargs=(cal, w0, w1)) as pool:
        res = pool.map(load_one, tick, chunksize=4)
    ST = {r["t"]: r for r in res if r is not None}
    print("[資料] us-stock-data {}｜有 OHLC {} 檔、可用 {}｜判定窗 {}～{}｜{:.0f}s".format(
        U.data_commit()[:10], len(tick), len(ST), cal[w0].date(), cal[w1].date(), time.time() - t0), flush=True)
    return cal, n, w0, w1, ST


# ═════════════ pre：頻率＋算術 ═════════════
def freq(ST, cal, w0, w1, n):
    wE, wB = w1 - HMAX, w1 - FORM_N
    out = {}
    for tag, types, end, fn in (("甲", TA, wE, keep_A), ("乙", TB, wB, keep_B)):
        DPY = (end - w0 + 1) / ((cal[end] - cal[w0]).days / 365.25)
        for typ in types:
            accs, per, per_s, ks = {}, [], [], []
            for s in sorted(ST):
                R = ST[s]; S = R["S"]
                k, a = fn(R, typ, w0, end, n)
                for k_, v_ in a.items():
                    accs[k_] = accs.get(k_, 0) + v_
                ks.append(k)
                ym = float(np.sum(S.member[w0:end + 1] & S.valid[w0:end + 1])) / DPY
                ysp = max(0, min(S.last, end) - max(int(S.bars[0]), w0) + 1) / DPY
                if ym > 0:
                    per.append((ym, len(k)))
                if ysp > 0:
                    per_s.append((ysp, len(k)))
            P_ = np.array(per); one = P_[P_[:, 0] >= 1.0]; rate = one[:, 1] / one[:, 0]
            Q_ = np.array(per_s)
            allT = [e["T"] if tag == "甲" else e["S"] for k in ks for e in k]
            blkH = {H: int(len(set((np.array(allT) - w0) // H))) if allT else 0 for H in ((60, 120) if tag == "甲" else (20,))}
            out[f"{tag}_{typ}"] = {"帳": accs, "保留": int(len(allT)), "有事件檔數": int(sum(1 for k in ks if k)),
                                  "每檔每年_合併比率_在指數日": round(float(P_[:, 1].sum() / P_[:, 0].sum()), 4),
                                  "每檔每年_平均_曝露≥1年": round(float(rate.mean()), 4), "每檔每年_中位_曝露≥1年": round(float(np.median(rate)), 4),
                                  "每檔每年_合併比率_台股Y11跨距式": round(float(Q_[:, 1].sum() / Q_[:, 0].sum()), 4),
                                  "在指數股票年": round(float(P_[:, 0].sum()), 1),
                                  "有事件的區段數": blkH, "n_eff上限_依區段": {str(H): int(min(len(allT), b)) for H, b in blkH.items()}}
            print("[頻率] {} {:6s} 保留 {:>7,}｜每檔每年 {:.3f}｜區段 {}｜{}".format(tag, NAME[typ], len(allT),
                  out[f"{tag}_{typ}"]["每檔每年_合併比率_在指數日"], blkH, accs), flush=True)
    return out


def arith(cal, w0, w1):
    wE, wB = w1 - HMAX, w1 - FORM_N
    a = {}
    for H in HOR:
        m = -(-(wE - w0 + 1) // H)
        a[f"甲_H{H}"] = {"可用日（同一批事件 T ≤ 窗尾−120）": int(wE - w0 + 1), "區段長": H, "最多區段": int(m),
                        "依構造最好": "出口①" if m < 30 else ("出口②" if m < 100 else "出口③")}
        m2 = -(-(w1 - H - w0 + 1) // H)
        a[f"甲_H{H}"]["另一讀法（T ≤ 窗尾−H）最多區段"] = int(m2)
    m = -(-(wB - w0 + 1) // EX_N)
    a["乙_20日"] = {"可用日（S ≤ 窗尾−40）": int(wB - w0 + 1), "區段長": 20, "最多區段": int(m), "依構造最好": "出口③" if m >= 100 else "出口②"}
    return a


# ═════════════ 本體：橫斷面 ═════════════
class Mat:
    """十分位（V8：T 日 in_index ∧ 波動可算）、原始觸發、對照可用（120 日／40 日）。"""

    def __init__(self, ST, n, w0, wE, wB):
        self.sids = sorted(ST); self.ix = {s: i for i, s in enumerate(self.sids)}
        N = len(self.sids); self.N, self.n = N, n
        SS = [ST[s]["S"] for s in self.sids]
        self.H = np.vstack([x.h for x in SS]); self.C = np.vstack([x.c for x in SS]); self.O = np.vstack([x.o for x in SS])
        self.L = np.vstack([x.l for x in SS])
        V = np.vstack([ST[s]["vol"] for s in self.sids]); MEMV = np.vstack([x.member & x.valid for x in SS])
        self.DEC = np.full((N, n), -1, np.int8)
        for t in range(w0, max(wE, wB) + 1):
            v = V[:, t]; ok = np.flatnonzero(np.isfinite(v) & MEMV[:, t])
            if len(ok) == 0:
                continue
            order = ok[np.lexsort((ok, v[ok]))]
            self.DEC[order, t] = (np.arange(len(order)) * 10) // len(order)
        self.TRIG = np.zeros((N, n), bool)
        for s in self.sids:
            for typ in TA:
                for e in ST[s]["A"][typ]:
                    self.TRIG[self.ix[s], e["T"]] = True
        self.OK = np.zeros((N, n), bool); self.OK40 = np.zeros((N, n), bool)
        for s in self.sids:
            S = ST[s]["S"]; i = self.ix[s]
            for Hh, M in ((HMAX, self.OK), (FORM_N, self.OK40)):
                t = np.arange(1, n - Hh - 1)
                brk = ((S.cs_pb[t + Hh] - S.cs_pb[t]) > 0) | ((S.cs_ms[t + Hh] - S.cs_ms[t]) > 0)
                M[i, t] = S.valid[t] & S.member[t] & S.valid[t + 1] & ~brk
        self._pool = {}

    def pool(self, t, d):
        k = (t, d)
        if k not in self._pool:
            self._pool[k] = np.flatnonzero((self.DEC[:, t] == d) & ~self.TRIG[:, t] & self.OK[:, t])
        return self._pool[k]

    def hit(self, i, t, H, tgt):
        seg = self.H[i, t + 1:t + H + 1]
        return int(np.isfinite(seg).any() and np.nanmax(seg) >= tgt)


def draw_ctl(M, i, t, rng):
    d = int(M.DEC[i, t])
    if d < 0:
        return None, 0, -1
    pool = M.pool(t, d); pool = pool[pool != i]
    if len(pool) == 0:
        return None, 0, -1
    k = int(rng.integers(len(pool)))
    return int(pool[k]), len(pool), k


def judge(X, cal, w0, H, col="d", hitcols=None):
    if len(X) == 0:
        return {"n": 0, "出口": "出口①", "結果": "—（出口①：樣本不足以分辨）"}
    cs = R11.cl_stats(X[col].to_numpy(float), X["month"].to_numpy())
    blk = int(((X["t"] - w0) // H).nunique()); n_eff = min(len(X), blk)
    out = {"n": int(len(X)), "D": cs["mean"], "中位": cs["median"], "lo": cs["lo"], "hi": cs["hi"], "se_月": cs["se"], "months": cs["months"],
           "區段數": blk, "n_eff": n_eff}
    small = n_eff < 30
    if hitcols:
        a, b = int(X[hitcols[0]].sum()), int(X[hitcols[1]].sum())
        out.update({"事件達成數": a, "對照達成數": b, "事件達成率": float(X[hitcols[0]].mean()), "對照達成率": float(X[hitcols[1]].mean())})
        small = small or a < 30 or b < 30
    if small:
        out["出口"] = "出口①"; out["結果"] = "—（出口①：樣本不足以分辨）"
    else:
        out["出口"] = "出口②" if n_eff < 100 else "出口③"
        out["結果"] = "結果①（測不出）" if cs["lo"] <= 0 <= cs["hi"] else ("結果②（測得出（＋））" if cs["mean"] > 0 else "結果③（測得出（−））")
    return out


def first_day(arr_bool, off):
    k = np.flatnonzero(arr_bool)
    return int(k[0]) + off if len(k) else None


def run_A(ST, M, cal, w0, wE, n, keptA):
    res, rows_all = {}, {}
    for typ in TA:
        rng = np.random.default_rng(SEED)
        evs = sorted([dict(e, sid=s) for s in keptA[typ] for e in keptA[typ][s]], key=lambda e: (e["T"], e["sid"]))
        rows, nodraw = [], 0
        for e in evs:
            i = M.ix[e["sid"]]; T = e["T"]
            j, psz, pk = draw_ctl(M, i, T, rng)
            if j is None:
                nodraw += 1; continue
            tgt_c = M.C[j, T] * (1.0 + e["dist"])
            r = {"sid": e["sid"], "t": T, "date": str(cal[T].date()), "month": cal[T].strftime("%Y-%m"), "dist": e["dist"],
                 "target": e["target"], "low": e["low"], "c_T": M.C[i, T], "o_T1": M.O[i, T + 1],
                 "ctl": M.sids[j], "ctl_c_T": M.C[j, T], "ctl_target": tgt_c, "pool_n": psz, "pool_k": pk,
                 "open_hit": int(M.O[i, T + 1] >= e["target"]), "dl_in": int(e["dl_in"]),
                 "first_date": str(cal[e["first"]].date()),
                 "pts": json.dumps({k_: str(cal[v_].date()) for k_, v_ in e.get("pts", {}).items()}, ensure_ascii=False)}
            if typ == "cup":
                r["target_half"] = e["target_half"]
            hs = M.H[i, T + 1:T + HMAX + 1]; ls_ = M.C[i, T + 1:T + HMAX + 1]
            with np.errstate(invalid="ignore"):
                dh = first_day(hs >= e["target"], 1)
                dl = first_day(M.L[i, T + 1:T + HMAX + 1] <= e["low"], 1)
            for H in HOR:
                r[f"sig_{H}"] = M.hit(i, T, H, e["target"]); r[f"ctl_{H}"] = M.hit(j, T, H, tgt_c)
                r[f"d_{H}"] = r[f"sig_{H}"] - r[f"ctl_{H}"]
                r[f"low_first_{H}"] = int(dl is not None and dl <= H and (dh is None or dh > H or dl < dh))
                r[f"low_same_{H}"] = int(dl is not None and dh is not None and dl == dh and dl <= H)
                if typ == "cup":
                    r[f"sig_half_{H}"] = M.hit(i, T, H, e["target_half"])
            r["days_to_hit"] = dh
            rows.append(r)
        X = pd.DataFrame(rows)
        rows_all[typ] = X
        jj = {H: judge(X.assign(d=X[f"d_{H}"]), cal, w0, H, hitcols=(f"sig_{H}", f"ctl_{H}")) for H in HOR}
        dsc = {"事件數": int(len(X)), "池空而剔除": nodraw, "相異檔數": int(X["sid"].nunique()) if len(X) else 0,
               "目標距離％分佈": {q: float(np.percentile(X["dist"], p)) for q, p in (("p10", 10), ("p25", 25), ("中位", 50), ("p75", 75), ("p90", 90))} if len(X) else {},
               "開盤即達成比例": float(X["open_hit"].mean()) if len(X) else None,
               "未來120日內下市（保留）": int(X["dl_in"].sum()) if len(X) else 0}
        for H in HOR:
            hh = X[X[f"sig_{H}"] == 1]["days_to_hit"] if len(X) else pd.Series(dtype=float)
            dsc[f"H{H}"] = {"事件達成率": float(X[f"sig_{H}"].mean()) if len(X) else None, "對照達成率": float(X[f"ctl_{H}"].mean()) if len(X) else None,
                            "達成天數中位（事件）": float(hh.median()) if len(hh) else None,
                            "先碰型態低點比例": float(X[f"low_first_{H}"].mean()) if len(X) else None,
                            "同日碰低點與目標": int(X[f"low_same_{H}"].sum()) if len(X) else 0}
            if typ == "cup" and len(X):
                dsc[f"H{H}"]["半杯深達成率（描述）"] = float(X[f"sig_half_{H}"].mean())
        cell = jj[HJ]["結果"] if jj[HJ]["出口"] != "出口①" else "—（出口①：樣本不足以分辨）"
        res[typ] = {"H60（判定）": jj[60], "H120（描述：依構造不可判定）": jj[120], "格的出口": jj[HJ]["出口"], "格的結果": cell, "描述": dsc}
        print("[甲] {:6s} n {:,}｜H60 D {:+.4f} [{:+.4f},{:+.4f}] {} {}｜H120（描述）D {:+.4f}".format(
            NAME[typ], len(X), jj[60].get("D", np.nan), jj[60].get("lo", np.nan), jj[60].get("hi", np.nan), jj[60]["出口"], jj[60]["結果"],
            jj[120].get("D", np.nan)), flush=True)
    return res, rows_all


def outcome_B(S, cffS, g):
    s = g["S"]; lim = s + FORM_N
    if g["end"] is not None:
        lim = min(lim, g["end"])
    trig = g["trig"] if (g["trig"] is not None and s < g["trig"] <= lim) else None
    c = S.c[s + 1:lim + 1] if lim > s else np.empty(0)
    with np.errstate(invalid="ignore"):
        k = np.flatnonzero(c < g["low"])
    dd = s + 1 + int(k[0]) if len(k) else None
    if trig is not None and (dd is None or trig < dd):
        return "成形", trig, dd
    if dd is not None:
        return "破壞", trig, dd
    return "都沒發生", trig, dd


def ew_close(O, okM, CFF, CSPB, Hh):
    """EW_Hh(d) ＝ okM[d] 的股票、(d, d+Hh−1] 內無 hard_break：CFF(d+Hh−1)／O(d) − 1 的等權平均（V9／B1）。"""
    n = O.shape[0]; out = np.full(n, np.nan); k = Hh - 1
    Od = np.where(okM[:n - k], O[:n - k], np.nan)
    with np.errstate(invalid="ignore", divide="ignore"):
        r = CFF[k:] / Od - 1.0
    r[(CSPB[k:] - CSPB[:n - k]) > 0] = np.nan
    cnt = np.isfinite(r).sum(axis=1); s = np.nansum(r, axis=1)
    out[:n - k] = np.where(cnt > 0, s / np.maximum(cnt, 1), np.nan)
    return out


def ew_close_brute(stocks, d, Hh):
    tot = k = 0
    for o, c, mem, pb in stocks:
        if not (mem[d] and np.isfinite(c[d]) and np.isfinite(o[d]) and o[d] > 0):
            continue
        if any(pb[d + 1:d + Hh]):
            continue
        j = d + Hh - 1
        while j >= 0 and not np.isfinite(c[j]):
            j -= 1
        tot += c[j] / o[d] - 1.0; k += 1
    return tot / k if k else np.nan


def run_B(ST, cal, w0, wB, n, EW, keptB):
    res, rows_all = {}, {}
    for typ in TB:
        rows = []
        for s in sorted(keptB[typ]):
            R = ST[s]; S = R["S"]
            for g in keptB[typ][s]:
                t = g["S"]
                R_ = R["cff"][t + EX_N] / S.o[t + 1] - 1.0
                oc, tg, dd = outcome_B(S, R["cff"], g)
                rows.append({"sid": s, "t": t, "date": str(cal[t].date()), "month": cal[t].strftime("%Y-%m"),
                             "R": R_, "EW": EW[t + 1], "X": R_ - COST - EW[t + 1], "結局": oc,
                             "成形日": str(cal[tg].date()) if tg is not None else "", "破壞日": str(cal[dd].date()) if dd is not None else "",
                             "low": g["low"], "first": str(cal[g["first"]].date()),
                             "end": str(cal[g["end"]].date()) if g["end"] is not None else ""})
        X = pd.DataFrame(rows).sort_values(["t", "sid"]).reset_index(drop=True)
        rows_all[typ] = X
        j = judge(X, cal, w0, EX_N, col="X")
        rate = {}
        for oc in ("成形", "破壞", "都沒發生"):
            ind = (X["結局"] == oc).astype(float).to_numpy()
            cs = R11.cl_stats(ind, X["month"].to_numpy())
            rate[oc] = {"率": cs["mean"], "lo": cs["lo"], "hi": cs["hi"], "筆數": int(ind.sum())}
            sub = X[X["結局"] == oc]
            rate[oc]["20日超額（描述）"] = float(sub["X"].mean()) if len(sub) else None
        res[typ] = {"判定": j, "率": rate, "平均R毛": float(X["R"].mean()), "平均EW": float(X["EW"].mean())}
        print("[乙] {:6s} n {:,}｜成形 {:.1%} 破壞 {:.1%}｜X {:+.4f} [{:+.4f},{:+.4f}] {} {}".format(
            NAME[typ], len(X), rate["成形"]["率"], rate["破壞"]["率"], j.get("D", np.nan), j.get("lo", np.nan), j.get("hi", np.nan), j["出口"], j["結果"]), flush=True)
    return res, rows_all


# ═════════════ 假訊號臂（V10）═════════════
def run_fake(ST, M, cal, w0, wE, wB, EW, rowsA, rowsB):
    out = []
    mon = np.array([cal[t].strftime("%Y-%m") for t in range(len(cal))])
    for tag, types, rowsX, OKM, end in (("甲", TA, rowsA, M.OK, wE), ("乙", TB, rowsB, M.OK40, wB)):
        for ti, typ in enumerate(types):
            X = rowsX[typ]
            real = {s: g.sort_values("t") for s, g in X.groupby("sid")}
            base = {}
            for s in real:
                i = M.ix[s]; idx = np.arange(w0, end + 1)
                ok = OKM[i, w0:end + 1] & ((M.DEC[i, w0:end + 1] >= 0) if tag == "甲" else True)
                base[s] = idx[ok]
            for vi, vn in enumerate(FVERS):
                cand = {}
                for s, g in real.items():
                    c = base[s]
                    if vi == 0:
                        c = c[~MB.excl_mask(c, g["t"].to_numpy())]
                    cand[s] = c
                short = 0
                for r in range(FAKE_R):
                    rows = []
                    for s in sorted(real):
                        g = real[s]; i = M.ix[s]
                        rng = np.random.default_rng([SEED + r, zlib.crc32(s.encode()), ti + (0 if tag == "甲" else 10), vi])
                        if vi == 2:                           # 同檔同月（台股原登錄）：每個 (檔, 曆月) 抽該月真事件數
                            days, dists = [], []
                            for mo, gm in g.groupby("month", sort=True):
                                cm = cand[s][mon[cand[s]] == mo]
                                k = min(len(gm), len(cm)); short += int(len(gm) > len(cm)) if r == 0 else 0
                                pick = np.sort(rng.choice(cm, size=k, replace=False)) if k else np.array([], int)
                                days += list(pick)
                                if tag == "甲":
                                    dists += list(gm["dist"].to_numpy()[:k])
                        else:
                            k = min(len(g), len(cand[s])); short += int(len(g) > len(cand[s])) if r == 0 else 0
                            days = list(np.sort(rng.choice(cand[s], size=k, replace=False))) if k else []
                            dists = list(g["dist"].to_numpy()[:k]) if tag == "甲" else []
                        for q, t in enumerate(days):
                            t = int(t)
                            if tag == "甲":
                                j, _, _ = draw_ctl(M, i, t, rng)
                                if j is None:
                                    continue
                                dist = dists[q]; tg = M.C[i, t] * (1 + dist); tc = M.C[j, t] * (1 + dist)
                                rr = {"t": t, "month": mon[t]}
                                for H in HOR:
                                    rr[f"sig_{H}"] = M.hit(i, t, H, tg); rr[f"ctl_{H}"] = M.hit(j, t, H, tc)
                                    rr[f"d_{H}"] = rr[f"sig_{H}"] - rr[f"ctl_{H}"]
                                rows.append(rr)
                            else:
                                S = ST[s]["S"]
                                R_ = ST[s]["cff"][t + EX_N] / S.o[t + 1] - 1.0
                                rows.append({"t": t, "month": mon[t], "X": R_ - COST - EW[t + 1]})
                    F = pd.DataFrame(rows)
                    if tag == "甲":
                        for H in HOR:
                            jf = judge(F.assign(d=F[f"d_{H}"]), cal, w0, H, hitcols=(f"sig_{H}", f"ctl_{H}")) if len(F) else {"n": 0}
                            out.append({"版本": vn, "r": r, "格": f"甲_{typ}_H{H}", "n": jf.get("n"), "D": jf.get("D"), "lo": jf.get("lo"), "hi": jf.get("hi"),
                                        "判過": bool(jf.get("n", 0) and not (jf["lo"] <= 0 <= jf["hi"])),
                                        "判過_正": bool(jf.get("n", 0) and not (jf["lo"] <= 0 <= jf["hi"]) and jf["D"] > 0)})
                    else:
                        jf = judge(F, cal, w0, EX_N, col="X") if len(F) else {"n": 0}
                        out.append({"版本": vn, "r": r, "格": f"乙_{typ}", "n": jf.get("n"), "D": jf.get("D"), "lo": jf.get("lo"), "hi": jf.get("hi"),
                                    "判過": bool(jf.get("n", 0) and not (jf["lo"] <= 0 <= jf["hi"])),
                                    "判過_正": bool(jf.get("n", 0) and not (jf["lo"] <= 0 <= jf["hi"]) and jf["D"] > 0)})
                out.append({"版本": vn, "r": -1, "格": f"{tag}_{typ}_可抽日不足檔數", "n": short})
            print("[假訊號臂] {} {} 完成".format(tag, NAME[typ]), flush=True)
    return pd.DataFrame(out)


# ═════════════ 美股資料型態 fixture ═════════════
def usx_fixtures(ST_sample):
    """UX1 EW_close 向量法＝獨立迴圈法｜UX2 keep_A／keep_B 的順序（R1、合併、型態視窗 S1、未來窗、T+1）｜
    UX3 前視（真實美股還原價＋量）：截斷到 d 或 d 以後換成別檔 ⇒ T ≤ d 的五型觸發、乙 六型 S 完全相同；破壞版（轉折提早一根確認）要被抓到。"""
    out = []
    rng = np.random.default_rng(3)
    n, S_ = 70, 6
    O = np.exp(rng.normal(0, 0.03, (n, S_)).cumsum(axis=0)) * 50; C = O * np.exp(rng.normal(0, 0.01, (n, S_)))
    C[10:13, 1] = np.nan; O[10:13, 1] = np.nan; C[40:, 2] = np.nan; O[40:, 2] = np.nan; C[:25, 3] = np.nan; O[:25, 3] = np.nan
    MEM = np.ones((n, S_), bool); MEM[:30, 4] = False
    PB = np.zeros((n, S_), bool); PB[35, 5] = True
    okO = np.isfinite(C) & np.isfinite(O) & (O > 0); CFF = pd.DataFrame(C).ffill().to_numpy()
    stocks = [(O[:, j], C[:, j], MEM[:, j], PB[:, j]) for j in range(S_)]
    worst = 0.0
    for Hh in (1, 5, 20):
        e = ew_close(O, okO & MEM, CFF, np.cumsum(PB, axis=0), Hh)
        for d in range(n - Hh + 1):
            b = ew_close_brute(stocks, d, Hh)
            worst = max(worst, abs(e[d] - b) if np.isfinite(b) else (0 if np.isnan(e[d]) else 1))
    assert worst < 1e-12, worst
    out.append("UX1 EW_close 向量法＝獨立迴圈法（在指數／停牌／下市／上市前／斷點排除）最大差 {:.1e}".format(worst))
    # UX2 狀態：手造 Stk（第 150 根沒有 K 棒；第 60 根不在指數；第 200 根波動不可算）
    m = 400
    c = np.linspace(100, 90, m); o = c + 0.1; h = c + 0.5
    A = {"O": o.copy(), "H": h.copy(), "C": c.copy(), "valid": np.ones(m, bool), "bars": np.arange(m), "pb": np.zeros(m, bool)}
    A["C"][150] = np.nan; A["O"][150] = np.nan; A["valid"][150] = False; A["bars"] = np.flatnonzero(A["valid"])
    mem = np.ones(m, bool); mem[60] = False
    Sx = MB.Stk("fx", A, c - 0.5, mem, np.full(m, np.datetime64("2010-01-01"), dtype="datetime64[ns]"), 0, m - 1)
    vol = np.full(m, 0.01); vol[200] = np.nan
    R = {"S": Sx, "vol": vol,
         "A": {"w": [dict(x, target=120.0) for x in [{"T": 20, "first": 5}, {"T": 35, "first": 30}, {"T": 45, "first": 10}, {"T": 60, "first": 50},
                     {"T": 155, "first": 145}, {"T": 200, "first": 190}, {"T": 230, "first": 220}, {"T": 231, "first": 221}]]},
         "B": {"w": [{"S": 20, "first": 5, "id": (5, 9)}, {"S": 25, "first": 6, "id": (5, 9)}, {"S": 60, "first": 50, "id": (50, 55)},
                     {"S": 45, "first": 40, "id": (40, 44)}, {"S": 145, "first": 140, "id": (140, 141)},
                     {"S": 155, "first": 148, "id": (148, 149)}, {"S": 320, "first": 300, "id": (300, 301)}]}}
    k, acc = keep_A(R, "w", 0, 279, m)
    assert [e["T"] for e in k] == [20, 230], ([e["T"] for e in k], acc)
    assert (acc["窗內但不在母體"], acc["合併掉"], acc["剔除_型態視窗斷點"], acc["剔除_未來窗斷點"], acc["剔除_20日波動不可算"]) == (1, 2, 1, 1, 1), acc
    kb, accb = keep_B(R, "w", 0, 350, m)
    assert [g["S"] for g in kb] == [20, 45, 320], ([g["S"] for g in kb], accb)
    assert (accb["窗內但不在母體"], accb["剔除_未來窗斷點"], accb["剔除_型態視窗斷點"]) == (1, 1, 1), accb
    out.append("UX2 保留順序（台股 Y2＋S1）：甲 [20,35,45,60,155,200,230,231] ⇒ 保留 [20,230]（合併 35、231；45 未來窗缺日；60 不在母體；155 型態視窗缺日；200 波動不可算）｜"
               "乙 每組只取第一個 S ⇒ 保留 [20,45,320]（60 不在母體；145 未來窗缺日；155 型態視窗缺日）")
    # UX3 前視（真實美股）
    n_cmp = n_ev = 0; bad = 0
    for t in ST_sample:
        df = U.load_ohlc(t, scope="panel"); cal = _G["cal"]
        A0 = RU.prep(df, cal); bars = A0["bars"]
        if len(bars) < 600:
            continue
        V = volume_aligned(t, cal, A0["valid"]); L = MB.low_aligned(df, cal)
        donor_t = ST_sample[(ST_sample.index(t) + 1) % len(ST_sample)]
        dA = RU.prep(U.load_ohlc(donor_t, scope="panel"), cal); dV = volume_aligned(donor_t, cal, dA["valid"])
        dL = MB.low_aligned(U.load_ohlc(donor_t, scope="panel"), cal)

        def snap(O_, H_, L_, C_, V_, d):
            valid = np.isfinite(C_); b = np.flatnonzero(valid)
            res = []
            for kind in ("w", "hs", "flag"):
                r = PX.detect_turn(kind, C_[b])
                res.append(sorted((kind, int(b[e["T"]])) for e in r["events"] if b[e["T"]] <= d))
                res.append(sorted((kind, int(b[g["S"]])) for g in r["groups"] if g["S"] is not None and b[g["S"]] <= d))
            ab, bb, ac, bc = detect_box_cup(O_, H_, L_, C_, V_, valid, cal, set())
            res.append(sorted(e["T"] for e in ab if e["T"] <= d)); res.append(sorted(g["S"] for g in bb if g["S"] <= d))
            res.append(sorted(e["T"] for e in ac if e["T"] <= d)); res.append(sorted(g["S"] for g in bc if g["S"] <= d))
            rt = PX.trend_forming(O_[b], H_[b], C_[b])
            res.append(sorted(int(b[g["S"]]) for g in rt["groups"] if g["S"] is not None and b[g["S"]] <= d))
            return res
        base = snap(A0["O"], A0["H"], L, A0["C"], V, 10 ** 9)
        n_ev += sum(len(x) for x in base)
        for d in rng.choice(bars[400:-50], 4, replace=False):
            d = int(d)
            full = [[x for x in grp if (x[1] if isinstance(x, tuple) else x) <= d] for grp in base]
            cut = [a.copy() for a in (A0["O"], A0["H"], L, A0["C"], V)]
            for a in cut:
                a[d + 1:] = np.nan
            assert snap(*cut, d) == full, ("截斷", t, d)
            s = A0["C"][d] / np.nanmedian(dA["C"])
            mut = [a.copy() for a in (A0["O"], A0["H"], L, A0["C"], V)]
            for a, dd in zip(mut, (dA["O"] * s, dA["H"] * s, dL * s, dA["C"] * s, dV)):
                a[d + 1:] = dd[d + 1:]
            assert snap(*mut, d) == full, ("突變", t, d)
            n_cmp += 2
        # 鑑別力：轉折序列（W 底／頭肩底／旗形共用）以 lag＝k−1（提早一根確認）時，截斷到確認根 ⇒ 必須出現差異；正式版 ⇒ 零差異
        cb = A0["C"][bars]
        lo_, hi_ = PX.local_ext(cb)
        for kind, fl in (("L", lo_), ("H", hi_)):
            for s_ in np.flatnonzero(fl)[5:25]:
                d = int(s_ + PX.K - 1)
                if d + 1 >= len(cb):
                    continue
                f1 = {k_: v_ for k_, v_ in PX.pivot_seq(cb, kind, lag=PX.K - 1).items() if k_ <= d}
                f2 = PX.pivot_seq(cb[:d + 1], kind, lag=PX.K - 1)
                bad += int(f1 != f2)
                g1 = {k_: v_ for k_, v_ in PX.pivot_seq(cb, kind).items() if k_ <= d}
                g2 = PX.pivot_seq(cb[:d + 1], kind)
                assert g1 == g2, ("正式版截斷後轉折序列不同", t, d)
    assert n_cmp > 0 and n_ev > 0 and bad > 0, (n_cmp, n_ev, bad)
    out.append("UX3 前視（真實美股還原價＋量 {} 檔）：{} 次比對（截斷＋換成別檔）六型觸發與 S 全同（該批 {} 筆）；轉折序列破壞版（確認提早一根）截斷到確認根抓到 {} 次差異、正式版 0".format(
        len(ST_sample), n_cmp, n_ev, bad))
    for s in out:
        print("✅", s, flush=True)
    return out


def main():
    global FAKE_R
    t00 = time.time()
    U.assert_pinned()
    from backtest import selftest_patterns_x as STX
    t1, _ = STX.run_all()
    print("[T1 台股合成型態] {}".format(t1), flush=True)
    bad = [k for k, v in t1.items() if not v]
    procs = int(sys.argv[sys.argv.index("--procs") + 1]) if "--procs" in sys.argv else 2
    lim = int(sys.argv[sys.argv.index("--limit") + 1]) if "--limit" in sys.argv else None
    if "--reps" in sys.argv:
        FAKE_R = int(sys.argv[sys.argv.index("--reps") + 1])
    cal, n, w0, w1, ST = load_all(procs, lim)
    _G.update(cal=cal, w0=w0, w1=w1)
    rs = np.random.default_rng(20260927)
    samp = [str(x) for x in rs.choice(sorted(ST), 8, replace=False)]
    ux = usx_fixtures(samp)
    os.makedirs(OUT, exist_ok=True); os.makedirs(WORK, exist_ok=True)
    wE, wB = w1 - HMAX, w1 - FORM_N
    fr = freq(ST, cal, w0, w1, n)
    ar = arith(cal, w0, w1)
    # V2 另一讀法（Tiingo 原始量）對事件的影響：只數原始偵測（窗內、在母體）差異
    vdiff = {"box_T": 0, "cup_T": 0, "boxS": 0, "cupS": 0, "Tiingo檔數": 0}
    for s, R in ST.items():
        if R["alt"] is None:
            continue
        vdiff["Tiingo檔數"] += 1
        S = R["S"]
        inw = lambda x, e: w0 <= x <= e and S.member[x] and S.valid[x]
        a = {"box_T": {e["T"] for e in R["A"]["box"]}, "cup_T": {e["T"] for e in R["A"]["cup"]},
             "boxS": {g["S"] for g in R["B"]["box"]}, "cupS": {g["S"] for g in R["B"]["cup"]}}
        for k_, v_ in R["alt"].items():
            e_ = wE if k_.endswith("_T") else wB
            vdiff[k_] += len({x for x in a[k_] if inw(x, e_)} ^ {x for x in v_ if inw(x, e_)})
    alt_eT = {}
    for typ in TA:
        alt_eT[typ] = sum(len(keep_A(ST[s], typ, w0, w1 - HJ, n, hz=HJ)[0]) for s in ST)
    PRE = {"性質": "USREG-X pre：頻率＋可判定性算術（⛔ 未計算任何報酬／達成）", "資料commit": U.data_commit(),
           "判定窗": [str(cal[w0].date()), str(cal[w1].date())], "甲T可落": str(cal[wE].date()), "乙S可落": str(cal[wB].date()),
           "可用檔數": len(ST), "T1_台股合成型態": t1, "T1_美股資料型態": ux, "頻率": fr, "開跑前算術": ar,
           "V2_Tiingo原始量版_原始偵測對稱差（窗內在母體）": vdiff,
           "V6_另一讀法_甲T≤窗尾−60_保留件數": alt_eT}
    json.dump(PRE, open(os.path.join(OUT, "pre_freq.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    print("[pre] 算術 {}｜V2 量差 {}｜V6 另讀 {}".format(ar, vdiff, alt_eT), flush=True)
    if bad:
        raise SystemExit("⛔ T1 不過的型：{}（該型不跑）".format(bad))
    if "--pre" in sys.argv:
        return
    # ── 本體
    t0 = time.time()
    keptA = {typ: {} for typ in TA}; keptB = {typ: {} for typ in TB}
    for s in sorted(ST):
        for typ in TA:
            k, _ = keep_A(ST[s], typ, w0, wE, n)
            if k:
                keptA[typ][s] = k
        for typ in TB:
            k, _ = keep_B(ST[s], typ, w0, wB, n)
            if k:
                keptB[typ][s] = k
    sids = sorted(ST)
    SS = [ST[s]["S"] for s in sids]
    O = np.column_stack([x.o for x in SS]); okM = np.column_stack([x.okO & x.member for x in SS])
    CFF = np.column_stack([ST[s]["cff"] for s in sids]); CSPB = np.column_stack([x.cs_pb for x in SS])
    EW = ew_close(O, okM, CFF, CSPB, EX_N)
    M = Mat(ST, n, w0, wE, wB)
    print("[橫斷面] 十分位／觸發／可用矩陣、EW20｜{:.0f}s".format(time.time() - t0), flush=True)
    resA, rowsA = run_A(ST, M, cal, w0, wE, n, keptA)
    resB, rowsB = run_B(ST, cal, w0, wB, n, EW, keptB)
    shas = []
    for tag, rows in (("A", rowsA), ("B", rowsB)):
        for typ, X in rows.items():
            p = os.path.join(WORK, f"{tag}_{typ}.csv.gz"); X.to_csv(p, index=False)
            shas.append((os.path.basename(p), len(X), sha256f(p)))
    p = os.path.join(WORK, "ew20_close.csv")
    pd.DataFrame({"date": [str(d.date()) for d in cal], "EW20": EW, "n_members": okM.sum(axis=1)}).to_csv(p, index=False)
    shas.append((os.path.basename(p), n, sha256f(p)))
    FK = run_fake(ST, M, cal, w0, wE, wB, EW, rowsA, rowsB)
    p = os.path.join(OUT, "body_fake_arm.csv"); FK.to_csv(p, index=False)
    fk = {}
    for (vn, g), x in FK[FK["r"] >= 0].groupby(["版本", "格"]):
        fk.setdefault(vn, {})[g] = {"判過": int(x["判過"].sum()), "其中(+)": int(x["判過_正"].sum()), "次數": int(len(x)),
                                   "平均D": float(x["D"].mean()), "範圍": [float(x["D"].min()), float(x["D"].max())]}
    short = {f"{vn}｜{g}": int(x["n"].iloc[0]) for (vn, g), x in FK[FK["r"] < 0].groupby(["版本", "格"])}
    with io.open(os.path.join(OUT, "body_work_sha.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n"); w.writerow(["file（~/us_work/usx/，repo 外）", "rows", "sha256"]); w.writerows(shas)
    summ = {"性質": "USREG-X 本體（單筆層；甲 5＋乙 6 ＝ 美股 N_前段 +11）", "資料commit": U.data_commit(),
            "登錄": {"seq2": "a3c98a07e882a574", "seq3": "81bfc48eff6258f5", "seq4": "cbfc7610923b9e53", "seq5": "ffb22ecb1bd749ff",
                   "台股PREREGX_seq2": "7de459d6a4578cf6", "讀法": "seq214 §三 R1～R4、B1～B7＋USREG-M B1 斷點規則；台股 researchX Y1～Y11、patterns_x X1～X11"},
            "判定窗": [str(cal[w0].date()), str(cal[w1].date())], "可用檔數": len(ST), "成本來回": COST,
            "開跑前算術": ar, "甲": resA, "乙": resB, "假訊號臂": fk, "假訊號臂_可抽日不足檔數": short,
            "逐筆檔sha（repo外）": {a: {"rows": b, "sha256": c} for a, b, c in shas},
            "body_fake_arm.csv_sha256": sha256f(os.path.join(OUT, "body_fake_arm.csv")), "耗時s": round(time.time() - t00)}
    json.dump(summ, open(os.path.join(OUT, "body_summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    print("完成 {:.0f}s".format(time.time() - t00), flush=True)


if __name__ == "__main__":
    main()

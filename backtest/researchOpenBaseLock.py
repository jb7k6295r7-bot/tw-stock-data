# -*- coding: utf-8 -*-
"""營量 v1／營飆 v1（策略鎖內）只讀盤點二：open_base「權息同日」——裁定 seq412 §三；回測線計算子代理。
⭐ 只讀盤點、描述、⛔ 不改標籤、⛔ 不計 N。⛔ 不改任何鎖內檔（鎖內函式只呼叫；要改的那一支 load_bars 在本檔複製一份改）；⛔ 不 commit。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchOpenBaseLock [--procs 3]
    （OBL_REUSE=1 ⇒ 逐股階段讀 /tmp/lki_obl_*.pkl 暫存）

═══ 讀法（寫於 2026-10-21（台北），在算任何本件數字之前）═══
 問題（資料庫 1021-0009、回測 0124 §二）：權息同日（現增權值＋現金股利，2464 盟立 2026-09-02 類）官方參考價 ref_price 含現增權值，
   但漲停用不含現增的開盤競價基準 open_base 算 ⇒ 用 ref_price（或 adj 因子 ≈ ref÷前收）判漲跌幅／壞 K 的程式會誤判。
 鎖內 7 處逐一定性（只讀程式）：
   ① research11.load_bars 幽靈除權判定（L139）：r ＝ 未還原收盤 ÷（前收 × adj 因子），r ∉ [0.895, 1.105] ⇒ 壞根 ⇒ 訊號資格（k−20～k 無壞根）與 fixed_exit（出場前有壞根 ⇒ xpos＝−1）
      ⭐ 唯一真的會被權息同日帶偏的地方：除權息日收漲停（open_base×1.1）時 r ＝ open_base×1.1 ÷ ref ⇒ 現增權值 ＞ 約 0.45% 就 ＞ 1.105 ⇒ 誤判壞根
   ②③ research11.limit_price／limit_flags（L42、L48–57）＋ load_bars 呼叫處（L156）：參考價 ＝ 前一根未還原收盤；除權息日（adj 事件根）一律 skip（不判漲跌停）
      ⇒ 權息同日那一根本來就不判 ⇒ 依構造 0 誤判；另附描述版 B：除權息日改用 exright limit_up／limit_down 判（原本 skip ⇒ 這是「多判」不是「改判」，⛔ 不屬權息同日）
   ④⑤ evaluate._limit_down_locked、hold_exit（L17–18、L38）：只進 research34 面板的描述報酬 ret20／ret60；rev_hi24（AND 用）與面板列存在與否都不看它 ⇒ 對 AND 依構造 0
   ⑥ list_yl13_watch.feat L124：前瞻「即將達成」名單的明日漲停價顯示 ⇒ 不進歷史訊號 ⇒ 歷史筆數依構造 0（只在「明天是權息同日」時顯示值偏）
 資料（唯讀）：上市 exright ＝ tw-stock-data edc6f8002f data/universe/exright（2015-01～2026-09）＋ origin/main dbfb96cb81 data/early/exright（2003～2014）；
   上櫃 otcexright 的 open_base 欄全空（2008～2026）⇒ 上櫃無法判 ⇒ 另報「上櫃除權息日被判幽靈」的根數與上限版 U（假設那些全是誤判）
 版本（幽靈判定只改「該股該日有 exright 列、且 K 棒日 ＝ 事件日」的事件根）：
   O  原版 ＝ 本檔複製的 load_bars（⛔ 與 research11.load_bars 逐鍵逐位元相同，閘 L）
   A1 字面版：分母改 open_base（r ＝ 收盤 ÷ open_base，門檻同 0.895／1.105）
   A  主版（官方漲跌停帶）：收盤 ＞ limit_up × 1.105／1.10 或 ＜ limit_down × 0.895／0.90 ⇒ 幽靈（同原式的 0.5 點寬容）；limit_up ≥ 9000（無漲跌幅）⇒ 照原式
      ⭐ 2026-10-21 首跑後補的（未看任何組合層數字前）：首跑只有 A1，發現純現增除權日（open_base ＝ 前收）官方跌停是用 ref_price 算
      （例 3149 2026-07-17：limit_down 78.1 ＝ 86.68×0.9 進位），A1 會把「收跌停」誤判成幽靈（5 根）⇒ 字面 open_base 只對漲停側對；主版改用官方漲跌停帶，A1 並列
   B  描述版 ＝ A ＋ 除權息日漲跌停旗標改用 exright limit_up／limit_down 判（skip 不動 ⇒ 訊號資格不變）
   U  上櫃上限 ＝ A ＋ 上櫃除權息日（無 exright 列）原判幽靈者全部改判非幽靈
 權息同日（廣義，本件統計口徑）＝ 事件 kind 含「權」且 |open_base ÷ ref − 1| ＞ 0.3%（即含現增權值；tick 進位差 ＜ 0.3%）；kind＝權息（狹義同日）另列
 流程：
   ① 全母體（主：load_universe ∩ gate3；早年：上市＋上櫃 O 版面同式）逐股算各版的幽靈旗標、漲跌停旗標；有任一根不同的股 ⇒ research11.stock_features
      （load_bars 換成本檔版本）重算 S main 列 ⇒ O 版必須 ＝ 定版 S 檔該股的列（閘 S：整數欄逐值、g 欄 |差| ≤ 1e−12）
   ② 各版 S 列套 T1 資料尾補（rerun17.t1_censor／researchYear1M.and_censor 同式，壞根改用該版的 next_bad）⇒ 與 O 版比：新增／消失／出場改變
      ⇒ 用定版面板 research13.and_flags 判 AND；營量看 H60、營飆看 H120 且閘開（rerun17.regime_mask 的 t−1）
   ③ 某版窗內有影響 ⇒ 組變體 AND 檔（定版檔只換受影響股的區塊；未變列原樣保留；新增列 relvol 用 researchp1.attach_features）
      ⇒ 經 researchYL_integrate.main_world／early_world 同路徑（只換 AND 檔路徑）跑營量 r0、營飆 r0～199；
      另跑「O 版 AND 檔」一次 ⇒ 必須逐位元 ＝ resultsYL_integrate/seeds.csv.gz（閘 P）
   ⚠ 早年世界另有 R8 減資截斷（apply_events），照原路徑套在變體上
輸出 backtest/resultsOpenBaseLock/：bars.csv（翻轉根）、s_diff.csv（T1 後的 S 差）、and_impact.csv、seeds.csv.gz、cells.csv、summary.json、REPORT.md、run.log
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import pickle
import sys
import time
from multiprocessing import Pool

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import rerun17 as RR                           # noqa: E402

RR.use_snapshot()
from backtest import data as D                               # noqa: E402
from backtest import research11 as R                         # noqa: E402
from backtest import research13 as R13                       # noqa: E402
from backtest import universe_gate as UG                     # noqa: E402

TIME = "2026-10-21（台北）"
OUT = "backtest/resultsOpenBaseLock"
NSEED = 200
if os.environ.get("OBL_QUICK"):
    NSEED, OUT = 3, "/tmp/obl_quick"
EXR = os.path.expanduser("~/exrdata")
MAIN_SHA, EARLY_SRC = "edc6f8002fed8803795e3486ad57db513f7e9f65", "dbfb96cb81a7d3032e07fe47d1aeb5f0230545fa"
MSHA = "f65bb03e114a5e10336d661218c63e6e68b08b85"
EARLY_DATA = os.path.expanduser(f"~/earlydata/eotc_{MSHA[:10]}/otc/data")
EARLY_SIG = os.path.expanduser(f"~/earlydata/eotc_{MSHA[:10]}/sig_otc")
MAIN_SIG = os.path.join(RR.OUT, "sig_edc6f")
WORD = "只讀盤點、描述、不改標籤、不計 N"
MODES = ("O", "A1", "A", "B", "U")
VMODES = ("A1", "A", "B", "U")
SCOLS = ["sid", "k", "pos", "entry_pos", "g_H60", "g_H120", "xpos_H60", "xpos_H120", "score"]
ACOLS = ["sid", "k", "pos", "entry_pos", "month", "g_H60", "g_H120", "g_LD", "xpos_H60", "xpos_H120", "xpos_LD", "t_LD"]
UPF, DNF = 1.105 / 1.10, 0.895 / 0.90
SEGS = {"主": {"探索": ("2017-03-02", "2021-12-30"), "確認": ("2022-01-03", "2026-08-24")}, "早年": {"早年": ("2005-02-01", "2014-12-31")}}
STRAT = {"營量": (60, False), "營飆": (120, True)}
_G: dict = {}


def now_tpe():
    return pd.Timestamp.now(tz="Asia/Taipei").strftime("%Y-%m-%d %H:%M")


def log_to(path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    f = open(path, "a", encoding="utf-8"); T0 = time.time()

    def log(m):
        m = f"[{time.time() - T0:6.0f}s] {m}"; print(m, flush=True); f.write(m + "\n"); f.flush()
    return log


# ═════════════ exright ═════════════
def load_exr():
    fs = sorted(glob.glob(f"{EXR}/edc6f8/data/universe/exright/*.csv")) + sorted(glob.glob(f"{EXR}/main/data/early/exright/*.csv"))
    d = pd.concat([pd.read_csv(f, dtype=str) for f in fs], ignore_index=True)
    for c in ("pre_close", "ref_price", "open_base", "limit_up", "limit_down"):
        d[c] = pd.to_numeric(d[c], errors="coerce")
    d = d.drop_duplicates(["stock_id", "date"], keep="first")
    d["權息同日"] = d["kind"].astype(str).str.contains("權") & ((d["open_base"] / d["ref_price"] - 1).abs() > 0.003)
    return d


# ═════════════ load_bars（research11.load_bars 逐行複製；mode≠"O" 才走改動行）═════════════
def load_bars_x(sid, market, cal, mode="O", info=None):
    st = D.load_stock(sid, market, cal)
    if st is None:
        return None
    df = st.df
    traded = df["traded"].to_numpy()
    idx = np.flatnonzero(traded)
    if len(idx) < 260:
        return None
    raw = pd.read_csv(os.path.join(D.DATA, "stocks", f"{sid}.csv"), dtype={"date": str}, usecols=["date", "close"])
    raw["date"] = pd.to_datetime(raw["date"]); raw = raw.drop_duplicates("date").set_index("date")["close"]
    rc_full = pd.to_numeric(raw.reindex(cal), errors="coerce").to_numpy(float)
    c = df["close"].to_numpy()[idx]; o = df["open"].to_numpy()[idx]; h = df["high"].to_numpy()[idx]; l = df["low"].to_numpy()[idx]
    amt = df["amount"].to_numpy()[idx]; rc = rc_full[idx]
    dates = cal[idx]; n = len(idx)
    adj = D.load_adj(sid)
    ev_bar = np.zeros(n, bool); phantom = np.zeros(n, bool)
    EX = _G.get("EXD", {}).get(sid, {}) if mode != "O" else {}
    OTC = _G.get("OTCP", {}).get(sid, []) if mode == "U" else []
    exb = {}
    if adj is not None and len(adj):
        for d, f in zip(adj["date"], adj["factor"].astype(float)):
            k = int(np.searchsorted(dates, d))
            if k >= n:
                continue
            ev_bar[k] = True
            if k > 0 and not np.isnan(rc[k]) and not np.isnan(rc[k - 1]) and f > 0:
                r = rc[k] / (rc[k - 1] * f)
                ph = r < 0.895 or r > 1.105
                if mode != "O":
                    e = EX.get(pd.Timestamp(d).strftime("%Y-%m-%d"))
                    if e is not None and dates[k] == pd.Timestamp(d):
                        ob, lu, ld = e
                        if mode == "A1":
                            if np.isfinite(ob) and ob > 0:
                                r = rc[k] / ob; ph = r < 0.895 or r > 1.105; exb[k] = e
                        elif np.isfinite(lu) and np.isfinite(ld) and lu < 9000 and ld > 0:
                            ph = bool(rc[k] > lu * UPF or rc[k] < ld * DNF); exb[k] = e
                if ph:
                    phantom[k] = True
                    if mode == "U" and k not in exb and any(a <= int(idx[k]) <= b for a, b in OTC):
                        phantom[k] = False
    bad = phantom.copy()
    gap = np.diff(idx) - 1
    bad[1:] |= gap >= 5
    for b in D.breakpoints(df, st.event_dates):
        if D.applies(b):
            k = int(np.searchsorted(idx, b["pos"]))
            if k < n:
                bad[k] = True
    next_bad = np.full(n + 1, n + 10, int)
    for k in range(n - 1, -1, -1):
        next_bad[k] = k if bad[k] else next_bad[k + 1]
    skip = ev_bar.copy()
    if dates[0] > pd.Timestamp("2015-01-12"):
        skip[:5] = True
    up, dn = R.limit_flags(rc, dates, skip)
    if mode == "B":
        for k, e in exb.items():
            if np.isfinite(rc[k]) and np.isfinite(e[1]) and np.isfinite(e[2]):
                up[k] = abs(rc[k] - e[1]) < 1e-6; dn[k] = abs(rc[k] - e[2]) < 1e-6
    if info is not None:
        info["phantom"] = phantom; info["exb"] = exb
    return {"idx": idx, "dates": dates, "o": o, "c": c, "h": h, "l": l, "amt": amt, "rc": rc, "up": up, "dn": dn,
            "ev_bar": ev_bar, "skip": skip, "next_bad": next_bad, "df": df}


def _same(B0, B1):
    if (B0 is None) != (B1 is None):
        return False
    if B0 is None:
        return True
    for k in B0:
        a, b = B0[k], B1[k]
        if k == "df":
            if not a.equals(b):
                return False
        elif isinstance(a, np.ndarray):
            if a.shape != b.shape or not np.array_equal(a, b, equal_nan=(a.dtype.kind == "f")):
                return False
        elif isinstance(a, pd.DatetimeIndex):
            if not a.equals(b):
                return False
    return True


# ═════════════ 逐股 ═════════════
def _init(cal, data, exd, otcp):
    D.DATA = data; R._init(cal); _G.update(cal=cal, EXD=exd, OTCP=otcp)


def feats(sid, market, first, mode):
    orig = R.load_bars
    R.load_bars = lambda s, m, cal: load_bars_x(s, m, cal, mode)
    try:
        r = R.stock_features((sid, market, first))
    finally:
        R.load_bars = orig
    return [] if r is None else r["main"]


def censor(rows, B, ncal):
    """T1 資料尾補（t1_censor／and_censor 同式；用該版 next_bad）。回新 list（只 H60／H120）。"""
    out = []
    if B is None:
        return [dict(r) for r in rows]
    idx, nb, o, c = B["idx"], B["next_bad"], B["o"], B["c"]; n = len(idx)
    for r in rows:
        r = {k: r[k] for k in ACOLS + ["score"] if k in r}
        k = int(r["k"])
        for H in (60, 120):
            if r[f"xpos_H{H}"] < 0 and int(idx[k]) == int(r["pos"]):
                if D.exit_pos(k + 1, H) >= n and nb[max(0, k - 20)] > n - 1 and int(idx[n - 1]) == ncal - 1:
                    r[f"xpos_H{H}"] = ncal; r[f"g_H{H}"] = float(c[n - 1] / o[k + 1] - 1.0)
        out.append(r)
    return out


def per_stock(args):
    sid, market, first, check = args
    cal = _G["cal"]
    out = {"sid": sid, "bars": [], "rows": {}, "rows_c": {}, "gateL": None}
    infos, Bs = {}, {}
    for m in MODES:
        infos[m] = {}
        Bs[m] = load_bars_x(sid, market, cal, m, infos[m])
    if Bs["O"] is None:
        return out
    if check:
        out["gateL"] = _same(R.load_bars(sid, market, cal), Bs["O"])
    B0 = Bs["O"]; idx = B0["idx"]; changed = False
    for m in VMODES:
        B1 = Bs[m]
        fb = np.flatnonzero(infos["O"]["phantom"] != infos[m]["phantom"])
        fu = np.flatnonzero((B0["up"] != B1["up"]) | (B0["dn"] != B1["dn"]))
        for k in fb:
            out["bars"].append({"版": m, "sid": sid, "k": int(k), "pos": int(idx[k]), "date": str(B0["dates"][k].date()), "類": "幽靈",
                                "O": bool(infos["O"]["phantom"][k]), "新": bool(infos[m]["phantom"][k]), "收盤": float(B0["rc"][k]),
                                "前收": float(B0["rc"][k - 1]) if k > 0 else np.nan})
        for k in fu:
            out["bars"].append({"版": m, "sid": sid, "k": int(k), "pos": int(idx[k]), "date": str(B0["dates"][k].date()), "類": "漲跌停",
                                "O": f"{int(B0['up'][k])}{int(B0['dn'][k])}", "新": f"{int(B1['up'][k])}{int(B1['dn'][k])}", "收盤": float(B0["rc"][k]),
                                "前收": float(B0["rc"][k - 1]) if k > 0 else np.nan})
        if len(fb) or len(fu):
            changed = True
    exb = infos["A"]["exb"]
    for k in np.flatnonzero(infos["O"]["phantom"]):
        out["bars"].append({"版": "O幽靈", "sid": sid, "k": int(k), "pos": int(idx[k]), "date": str(B0["dates"][k].date()), "類": "幽靈",
                            "O": True, "新": ("有exright" if k in exb else "無exright"), "收盤": float(B0["rc"][k]),
                            "前收": float(B0["rc"][k - 1]) if k > 0 else np.nan})
    if changed or check:
        for m in MODES:
            rows = feats(sid, market, first, m)
            out["rows"][m] = rows
            out["rows_c"][m] = censor(rows, Bs[m], len(cal))
    return out


def _same_val(a, b):
    try:
        return a == b or (np.isnan(a) and np.isnan(b))
    except TypeError:
        return a == b


def run_world(name, data, sig_full, panel_path, procs, exd, log, check_n=40):
    D.DATA = data
    cal = D.load_calendar()
    stocks = pd.read_csv(os.path.join(D.DATA, "meta", "stocks.csv"), dtype=str)
    uni = D.load_universe().merge(UG.gate3(stocks)[["stock_id"]], on="stock_id")
    otcp = {}
    if name == "早年":
        per = json.load(open(os.path.expanduser(f"~/earlydata/eotc_{MSHA[:10]}/otc/otc_periods.json")))
        otcp = {s: [(int(cal.searchsorted(pd.Timestamp(a))), int(cal.searchsorted(pd.Timestamp(b), side="right")) - 1) for a, b in v] for s, v in per.items()}
    else:
        for s, mk in zip(uni["stock_id"], uni["market"]):
            if mk == "tpex":
                otcp[s] = [(0, len(cal) - 1)]
    rng = np.random.default_rng(20261021)
    chk = set(rng.choice(uni["stock_id"].to_numpy(), size=min(check_n, len(uni)), replace=False))
    tasks = [(s, m, f, s in chk) for s, m, f in zip(uni["stock_id"], uni["market"], uni["first_seen"])]
    cache = f"/tmp/lki_obl2_{'main' if name == '主' else 'early'}.pkl"
    if os.environ.get("OBL_REUSE") and os.path.exists(cache):
        res = pickle.load(open(cache, "rb")); log(f"  [{name}] 讀暫存 {cache}")
    else:
        res = []
        with Pool(procs, initializer=_init, initargs=(cal, data, exd, otcp)) as p:
            for i, r in enumerate(p.imap_unordered(per_stock, tasks, chunksize=8)):
                res.append(r)
                if (i + 1) % 500 == 0:
                    log(f"  [{name}] {i + 1}/{len(tasks)}")
        pickle.dump(res, open(cache, "wb"))
    D.DATA = data
    S = pd.read_csv(sig_full, dtype={"sid": str})
    bars = pd.DataFrame([b for r in res for b in r["bars"]])
    if len(bars):
        bars.insert(0, "世界", name)
    gL = [r["gateL"] for r in res if r["gateL"] is not None]
    badS = 0; nS = 0; diffs = []; VR = {m: {} for m in MODES}
    for r in res:
        if not r["rows"]:
            continue
        s = r["sid"]; nS += 1
        O = pd.DataFrame(r["rows"]["O"])
        ref = S[S["sid"] == s]
        if len(O) != len(ref):
            badS += 1
        elif len(O):
            a = O[SCOLS].sort_values(["k"]).reset_index(drop=True); b = ref[SCOLS].sort_values(["k"]).reset_index(drop=True)
            if not all((a[c].astype(str) == b[c].astype(str)).all() if c == "sid" else
                       np.allclose(a[c].to_numpy(float), b[c].to_numpy(float), equal_nan=True, rtol=0, atol=(1e-12 if c.startswith("g_") else 0))
                       for c in SCOLS):
                badS += 1
        for m in MODES:
            VR[m][s] = r["rows_c"][m]
        ok = {int(x["k"]): x for x in r["rows_c"]["O"]}
        for m in VMODES:
            nw = {int(x["k"]): x for x in r["rows_c"][m]}
            for k in sorted(set(ok) | set(nw)):
                a, b = ok.get(k), nw.get(k)
                if a is not None and b is not None:
                    ch = [c for c in ("xpos_H60", "xpos_H120", "g_H60", "g_H120", "entry_pos") if not _same_val(a[c], b[c])]
                    if not ch:
                        continue
                    kind = "改：" + "、".join(ch)
                else:
                    kind = "新增" if a is None else "消失"
                x = b if a is None else a
                diffs.append({"世界": name, "版": m, "sid": s, "k": k, "pos": int(x["pos"]), "entry_pos": int(x["entry_pos"]), "變": kind,
                              **{f"{c}_{t}": (y or {}).get(c, np.nan) for c in ("xpos_H60", "g_H60", "xpos_H120", "g_H120") for t, y in (("O", a), ("新", b))}})
    dd = pd.DataFrame(diffs)
    reg = RR.regime_mask(RR.load_bench(cal))
    if len(dd):
        pnl = pd.read_csv(panel_path, dtype={"stock_id": str})
        pnl["rev_hi24"] = pnl["rev_hi24"].fillna(False).astype(bool)
        fl, _ = R13.and_flags(dd[["sid", "pos"]].copy(), pnl)
        dd["AND"] = fl
        dd["閘開"] = reg[dd["entry_pos"].to_numpy(int) - 1]
        dd["訊號日"] = [str(cal[int(p)].date()) for p in dd["pos"]]; dd["進場日"] = [str(cal[int(p)].date()) for p in dd["entry_pos"]]
        seg = []
        for e_ in dd["entry_pos"]:
            sg = "窗外"
            for nm, (lo_, hi_) in SEGS[name].items():
                if int(cal.searchsorted(pd.Timestamp(lo_))) <= e_ <= int(cal.searchsorted(pd.Timestamp(hi_))):
                    sg = nm
            seg.append(sg)
        dd["段"] = seg
        for stg, (H, G) in STRAT.items():
            hit = dd["變"].isin(["新增", "消失"]) | dd["變"].str.contains(f"H{H}") | dd["變"].str.contains("entry")
            dd[f"影響{stg}"] = hit & dd["AND"] & (dd["段"] != "窗外") & (dd["閘開"] if G else True)
    info = {"母體": int(len(uni)), "上櫃股（有上櫃期間）": int(len(otcp)), "閘L 抽查股": len(gL), "閘L 不同": int(sum(1 for g in gL if not g)),
            "重算S的股": nS, "閘S 不同股": badS, "閘S 比法": "整數欄逐值相同、g 欄 |差| ≤ 1e−12（定版 S 為 CSV 讀回值）",
            "cal": [str(cal[0].date()), str(cal[-1].date())]}
    log(f"[{name}] {json.dumps(info, ensure_ascii=False)}")
    return {"cal": cal, "uni": uni, "bars": bars, "diff": dd, "info": info, "VR": VR, "reg": reg}


# ═════════════ 變體 AND ═════════════
def variant_and(wn, w, m, and_path, sfull_path, procs, log):
    """定版 AND 檔只換「受影響股」的區塊（未變列原樣）；回 DataFrame。"""
    from backtest import researchp1 as P1
    A0 = pd.read_csv(and_path, dtype={"sid": str})
    dd = w["diff"]
    if not len(dd):
        return A0, 0
    sids = sorted(set(dd[(dd["版"] == m) & dd["AND"]]["sid"]))
    if not sids:
        return A0, 0
    pnl = pd.read_csv(os.path.join(os.path.dirname(and_path), "panel_rev.csv.gz"), dtype={"stock_id": str})
    pnl["rev_hi24"] = pnl["rev_hi24"].fillna(False).astype(bool)
    blocks = {}; nch = 0
    for s in sids:
        rows = pd.DataFrame(w["VR"][m][s])
        fl, _ = R13.and_flags(rows[["sid", "pos"]].copy(), pnl)
        new = rows[fl][ACOLS].copy()
        old = A0[A0["sid"] == s].set_index("k")
        keep = []
        add = []
        for _, r in new.iterrows():
            k = int(r["k"])
            if k in old.index:
                o_ = old.loc[k].copy()
                for c in ("xpos_H60", "xpos_H120", "g_H60", "g_H120"):
                    if not _same_val(o_[c], r[c]):
                        o_[c] = r[c]; nch += 1
                o_["k"] = k
                keep.append(o_)
            else:
                add.append(r); nch += 1
        B = pd.DataFrame(keep).reset_index(drop=True) if keep else pd.DataFrame(columns=A0.columns)
        if add:
            Ad = pd.DataFrame(add).reset_index(drop=True)
            D.DATA = w["data"]
            miss, mism = P1.attach_features(Ad, Ad.copy(), w["cal"], w["uni"].set_index("stock_id")["market"], 1)
            if miss or mism:
                raise SystemExit(f"⛔ attach_features {s} {miss} {mism}")
            B = pd.concat([B, Ad[A0.columns]], ignore_index=True)
        nch += len(set(old.index) - set(new["k"].astype(int)))
        blocks[s] = B[A0.columns].sort_values("k").reset_index(drop=True)
    parts = []; done = set()
    for s, g in A0.groupby("sid", sort=False):
        if s in blocks:
            parts.append(blocks[s]); done.add(s)
        else:
            parts.append(g)
    for s in sids:
        if s not in done and len(blocks[s]):
            parts.append(blocks[s])
    A = pd.concat(parts, ignore_index=True)[A0.columns]
    for c in ("k", "pos", "entry_pos", "xpos_H60", "xpos_H120", "xpos_LD"):
        A[c] = A[c].astype(int)
    log(f"[變體 {wn}·{m}] 換股 {sids}｜列 {len(A0)}→{len(A)}｜變動列 {nch}")
    return A, nch


# ═════════════ 組合層 ═════════════
_W: dict = {}


def run_seed(args):
    from backtest import researchYL_integrate as IG
    wk, stg, r = args
    W = _W[wk]
    key = IG.YL if stg == "營量" else IG.YF
    o, au = IG.eng(W, key, r)
    eq = np.asarray(o["equity"], float)
    import hashlib
    row = {"世界鍵": wk, "策略": stg, "r": r, "eq_sha": hashlib.sha256(eq.tobytes()).hexdigest()[:16]}
    for sg, (x, y) in W["segp"].items():
        c_, m_, _ = RR.win_metrics(eq, o["first"], o["end"], x, y)
        row[f"{sg}_年化"] = float(c_); row[f"{sg}_回落"] = float(m_)
    return row


def build_world(wn, A, tag, procs, log):
    from backtest import researchYL_integrate as IG
    tmp = f"/tmp/lki_obl_sig_{'main' if wn == '主' else 'early'}_{tag}"
    os.makedirs(tmp, exist_ok=True)
    A.to_csv(os.path.join(tmp, "and_signals.csv.gz"), index=False)
    if wn == "主":
        p = os.path.join(tmp, "panel_rev.csv.gz")
        if not os.path.exists(p):
            os.symlink(os.path.join(MAIN_SIG, "panel_rev.csv.gz"), p)
        orig = RR.setup_and
        RR.setup_and = lambda cal, and_path, px, lg, t1=False: orig(cal, os.path.join(tmp, "and_signals.csv.gz"), px, lg, t1=t1)
        try:
            RR.use_snapshot()
            W, gate = IG.main_world(log)
        finally:
            RR.setup_and = orig
    else:
        from backtest import researchEarlyOTC_rerun as EO
        p = os.path.join(tmp, "panel_rev.csv.gz")
        if not os.path.exists(p):
            os.symlink(os.path.join(EARLY_SIG, "panel_rev.csv.gz"), p)
        orig = EO.odirs
        EO.odirs = lambda msha: tuple(tmp if i == 3 else x for i, x in enumerate(orig(msha)))
        try:
            W, gate = IG.early_world(log, procs)
        finally:
            EO.odirs = orig
    return W, gate


def sims(wk, procs):
    jobs = [(wk, "營量", 0)] + [(wk, "營飆", r) for r in range(NSEED)]
    with Pool(procs) as p:
        return p.map(run_seed, jobs, chunksize=4)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--procs", type=int, default=3); a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    log = log_to(os.path.join(OUT, "run.log"))
    log(f"[開始] {now_tpe()}（台北）｜讀法寫死 {TIME}")
    S_ = {"讀法寫死": TIME, "性質": WORD, "閘": {}}
    ex = load_exr()
    exd = {}
    for s, d, ob, lu, ld in zip(ex["stock_id"], ex["date"], ex["open_base"], ex["limit_up"], ex["limit_down"]):
        exd.setdefault(s, {})[d] = (float(ob), float(lu), float(ld))
    S_["exright"] = {"列": int(len(ex)), "期間": [ex["date"].min(), ex["date"].max()], "權息同日（廣義：含現增權值）": int(ex["權息同日"].sum()),
                     "其中 kind＝權息（狹義同日）": int((ex["權息同日"] & (ex["kind"] == "權息")).sum()), "其中 kind＝權（純現增等）": int((ex["權息同日"] & (ex["kind"] == "權")).sum())}
    log(f"[exright] {S_['exright']}")
    WR = {}
    WR["主"] = run_world("主", RR.H2D, os.path.join(MAIN_SIG, "signals_S.csv.gz"), os.path.join(MAIN_SIG, "panel_rev.csv.gz"), a.procs, exd, log)
    WR["主"]["data"] = RR.H2D
    WR["早年"] = run_world("早年", EARLY_DATA, os.path.join(EARLY_SIG, "signals_S_full.csv.gz"), os.path.join(EARLY_SIG, "panel_rev.csv.gz"), a.procs, exd, log)
    WR["早年"]["data"] = EARLY_DATA
    bars = pd.concat([w["bars"] for w in WR.values() if len(w["bars"])], ignore_index=True)
    dd = pd.concat([w["diff"] for w in WR.values() if len(w["diff"])], ignore_index=True) if any(len(w["diff"]) for w in WR.values()) else pd.DataFrame()
    exk = {(s, d): (k, q) for s, d, k, q in zip(ex["stock_id"], ex["date"], ex["kind"], ex["權息同日"])}
    exv = {(s, d): (pc, rf, ob, lu, ld) for s, d, pc, rf, ob, lu, ld in zip(ex["stock_id"], ex["date"], ex["pre_close"], ex["ref_price"], ex["open_base"], ex["limit_up"], ex["limit_down"])}
    if len(bars):
        bars["exright_kind"] = [exk.get((s, d), (None, None))[0] for s, d in zip(bars["sid"], bars["date"])]
        bars["權息同日"] = [exk.get((s, d), (None, None))[1] for s, d in zip(bars["sid"], bars["date"])]
        for j, c in enumerate(("ex_pre_close", "ex_ref", "ex_open_base", "ex_limit_up", "ex_limit_down")):
            bars[c] = [exv.get((s, d), (np.nan,) * 5)[j] for s, d in zip(bars["sid"], bars["date"])]
    bars.to_csv(os.path.join(OUT, "bars.csv"), index=False, encoding="utf-8-sig")
    dd.to_csv(os.path.join(OUT, "s_diff.csv"), index=False, encoding="utf-8-sig")
    for wn, w in WR.items():
        S_["閘"][f"L {wn} 複製版 load_bars ＝ 鎖內（不同股數／抽 {w['info']['閘L 抽查股']}）"] = w["info"]["閘L 不同"]
        S_["閘"][f"S {wn} O 版重算 S ＝ 定版 S 檔（不同股數／{w['info']['重算S的股']}）"] = w["info"]["閘S 不同股"]
    S_["世界"] = {wn: w["info"] for wn, w in WR.items()}
    BS = {}
    for wn in WR:
        b = bars[bars["世界"] == wn] if len(bars) else bars
        rec = {}
        for m in VMODES:
            x = b[(b["版"] == m)] if len(b) else b
            ph = x[x["類"] == "幽靈"] if len(x) else x
            rec[m] = {"幽靈翻轉根": int(len(ph)), "原壞→新好": int((ph["O"] == True).sum()) if len(ph) else 0,
                      "原好→新壞": int((ph["O"] == False).sum()) if len(ph) else 0,
                      "其中權息同日事件（廣義）": int((ph["權息同日"] == True).sum()) if len(ph) else 0,
                      "其中 kind＝權息": int((ph["exright_kind"] == "權息").sum()) if len(ph) else 0,
                      "漲跌停翻轉根": int((x["類"] == "漲跌停").sum()) if len(x) else 0}
        x = b[b["版"] == "O幽靈"] if len(b) else b
        rec["O版事件日幽靈"] = x["新"].value_counts().to_dict() if len(x) else {}
        BS[wn] = rec
    S_["翻轉根"] = BS
    log(f"[翻轉根] {json.dumps(BS, ensure_ascii=False, default=str)}")
    # 影響表
    IMP = {}; ai = []
    for wn, w in WR.items():
        x = w["diff"]
        for m in VMODES:
            for stg in STRAT:
                for sg in SEGS[wn]:
                    y = x[(x["版"] == m) & x[f"影響{stg}"] & (x["段"] == sg)] if len(x) else x
                    IMP[f"{wn}|{m}|{stg}|{sg}"] = int(len(y))
                    if len(y):
                        ai.append(y.assign(策略=stg))
    S_["窗內影響筆數"] = IMP
    AI = pd.concat(ai, ignore_index=True) if ai else pd.DataFrame()
    AI.to_csv(os.path.join(OUT, "and_impact.csv"), index=False, encoding="utf-8-sig")
    log(f"[窗內影響] {json.dumps(IMP, ensure_ascii=False)}")
    # ── 組合層 ──
    SE = []
    for wn, w in WR.items():
        and_path = os.path.join(MAIN_SIG if wn == "主" else EARLY_SIG, "and_signals.csv.gz")
        need = [m for m in VMODES if any(IMP[f"{wn}|{m}|{stg}|{sg}"] for stg in STRAT for sg in SEGS[wn])]
        if not need:
            log(f"[組合層 {wn}] 各版窗內影響 0 ⇒ 不跑"); continue
        A0 = pd.read_csv(and_path, dtype={"sid": str})
        for tag in ["O"] + need:
            A, nch = (A0, 0) if tag == "O" else variant_and(wn, w, tag, and_path, None, a.procs, log)
            W, gate = build_world(wn, A, tag, a.procs, log)
            k_ = f"{wn}_{tag}"; _W.clear(); _W[k_] = W
            S_.setdefault("世界閘", {})[k_] = gate
            SE += sims(k_, a.procs)
            log(f"[模擬 {k_}] 完成")
    if SE:
        SE = pd.DataFrame(SE)
        SE.to_csv(os.path.join(OUT, "seeds.csv.gz"), index=False, float_format="%.17g")
        from backtest import researchYL_integrate as IG
        ref = pd.read_csv("backtest/resultsYL_integrate/seeds.csv.gz", dtype={"eq_sha": str}, float_precision="round_trip")
        b50 = json.load(open("backtest/resultsYL_integrate/summary.json", encoding="utf-8"))["0050"]
        C = []
        for wk in SE["世界鍵"].unique():
            wn, tag = wk.split("_", 1)
            for stg in STRAT:
                g = SE[(SE["世界鍵"] == wk) & (SE["策略"] == stg)].set_index("r")
                key = IG.YL if stg == "營量" else IG.YF
                rr = ref[(ref["世界"] == wn) & (ref["格"] == key)].set_index("r")
                if tag == "O":
                    bad = int(sum(g.at[r, "eq_sha"] != rr.at[r, "eq_sha"] for r in g.index))
                    S_["閘"][f"P {wn}_{stg} O 版 AND 檔重跑 ＝ resultsYL_integrate eq_sha（不同顆數／{len(g)}）"] = bad
                for sg in SEGS[wn]:
                    c_, m_ = float(g[f"{sg}_年化"].median()), float(g[f"{sg}_回落"].median())
                    c0, m0 = float(rr.loc[g.index, f"{sg}_年化"].median()), float(rr.loc[g.index, f"{sg}_回落"].median())
                    bb = b50[wn][sg]
                    C.append({"世界": wn, "版": tag, "策略": stg, "段": sg, "顆數": len(g), "年化": c_, "回落": m_, "比值": c_ / abs(m_), "對0050": IG.label(c_, m_, bb),
                              "定版年化": c0, "定版回落": m0, "定版比值": c0 / abs(m0), "定版對0050": IG.label(c0, m0, bb),
                              "Δ年化": c_ - c0, "Δ回落": m_ - m0, "Δ比值": c_ / abs(m_) - c0 / abs(m0),
                              "配對差年化_中位": float((g[f"{sg}_年化"] - rr.loc[g.index, f"{sg}_年化"]).median()),
                              "年化有變顆數": int((g[f"{sg}_年化"] != rr.loc[g.index, f"{sg}_年化"]).sum()),
                              "0050年化": bb["cagr"], "0050回落": bb["mdd"]})
        C = pd.DataFrame(C); C["標籤變"] = C["對0050"] != C["定版對0050"]
        C.to_csv(os.path.join(OUT, "cells.csv"), index=False, encoding="utf-8-sig", float_format="%.10g")
        S_["表"] = C.to_dict("records")
        pd.set_option("display.width", 250); pd.set_option("display.max_columns", 30)
        log("\n" + C[["世界", "版", "策略", "段", "年化", "回落", "比值", "對0050", "Δ年化", "Δ回落", "Δ比值", "配對差年化_中位", "年化有變顆數", "標籤變"]].to_string(index=False))
    S_["完成（台北）"] = now_tpe()
    json.dump(S_, open(os.path.join(OUT, "summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    log(f"[閘] {S_['閘']}")
    bad = [k for k, v in S_["閘"].items() if v != 0]
    if bad:
        log(f"⛔ 閘不過 {bad}")
        raise SystemExit(1)
    log(f"[完] {now_tpe()}（台北）")


def sgn(v, d=1):
    return "—" if v is None or not np.isfinite(v) else f"{v * 100:+.{d}f}%"


def report():
    """由 summary.json／cells.csv／and_impact.csv 產 REPORT.md（--report 只做這步；主流程最後也呼叫）。"""
    S = json.load(open(os.path.join(OUT, "summary.json"), encoding="utf-8"))
    L = ["# 只讀盤點二：open_base「權息同日」對營量 v1、營飆 v1 的影響", "", f"產出 {S.get('完成（台北）')}（台北）。回測線計算子代理。⭐ {WORD}。⛔ 鎖內檔一字未改。", "",
         "## exright", "", "```", json.dumps(S["exright"], ensure_ascii=False, indent=1), "```", "",
         "## 翻轉根（幽靈判定、漲跌停旗標；A1 字面 open_base、A 官方漲跌停帶〔主〕、B＝A＋除權息日漲跌停、U＝A＋上櫃無 exright 幽靈全改非幽靈）", "",
         "```", json.dumps(S["翻轉根"], ensure_ascii=False, indent=1), "```", "",
         "## 窗內受影響筆數（T1 後；營飆只計閘開）", "", "| 世界｜版｜策略｜段 | 筆數 |", "|---|---|"]
    for k, v in S["窗內影響筆數"].items():
        L.append(f"| {k} | {v} |")
    p = os.path.join(OUT, "and_impact.csv")
    if os.path.exists(p) and os.path.getsize(p) > 5:
        d = pd.read_csv(p, dtype={"sid": str})
        L += ["", "### 明細", "", "| 世界 | 版 | 策略 | 段 | 代號 | 訊號日 | 進場日 | 變 | H60 出場 O→新 | H120 出場 O→新 |", "|---|---|---|---|---|---|---|---|---|---|"]
        for _, r in d.iterrows():
            L.append(f"| {r['世界']} | {r['版']} | {r['策略']} | {r['段']} | {r['sid']} | {r['訊號日']} | {r['進場日']} | {r['變']} | "
                     f"{sgn(r['g_H60_O'])}→{sgn(r['g_H60_新'])} | {sgn(r['g_H120_O'])}→{sgn(r['g_H120_新'])} |")
    p = os.path.join(OUT, "cells.csv")
    if os.path.exists(p):
        C = pd.read_csv(p)
        L += ["", "## 組合層（營飆 200 顆中位；比值 ＝ 年化 ÷ |回落|；Δ 對定版）", "",
              "| 世界 | 版 | 策略 | 段 | 年化 | 回落 | 比值 | 對 0050 | Δ年化 | Δ回落 | Δ比值 | 配對差中位 | 年化有變顆數 |", "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
        for _, r in C.iterrows():
            L.append(f"| {r['世界']} | {r['版']} | {r['策略']} | {r['段']} | {sgn(r['年化'])} | {sgn(r['回落'])} | {r['比值']:.3f} | {r['對0050']}{'（變）' if r['標籤變'] else ''} | "
                     f"{sgn(r['Δ年化'], 2)} | {sgn(r['Δ回落'], 2)} | {r['Δ比值']:+.3f} | {sgn(r['配對差年化_中位'], 2)} | {r['年化有變顆數']}／{r['顆數']} |")
    L += ["", "## 對帳", "", "```", json.dumps(S["閘"], ensure_ascii=False, indent=1), "```", "", f"⭐ {WORD}。"]
    open(os.path.join(OUT, "REPORT.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")


if __name__ == "__main__":
    if "--report" in sys.argv:
        report()
    else:
        main()
        report()

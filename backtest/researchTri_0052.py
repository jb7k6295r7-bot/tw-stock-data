# -*- coding: utf-8 -*-
"""PREREG三態輪動 seq4（sha adadbdbcd4ce9dc2）加 0052 ——【事後描述臂】（裁定 seq228 §二）。

⚠ 看過三態結果後才加 ⇒ ⛔ 不判、⛔ 不計 N、⛔ 不取代 seq3 結果（seq3 判定：W4×P3×U4×B現金 確認段 +44.65%，只看報酬贏 0050）

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchTri_0052
    查核：~/tw-p16/.venv/bin/python backtest/researchTri_0052_check.py

做法：
  ① seq3 挑出的訊號組 W4×P3×U4（訊號一律用 0050 判；狀態路徑與 seq3 同一條）× 6 種持有：B∈{0050, 0052, 現金} × C∈{0050, 0052}
     ⇒ 探索段、確認段各報（年化、回落、比值、對 0050、對純抱 00631L、2022 谷底）
  ② 事後：第一層 10×7×8 × 6 版 ＝ 3,360 格照 seq4 挑法（乙：探索年化最高；甲：使用者判準中比值最高；同分取轉換少）⇒ 報確認段；
     另報 6 版各自的探索段第 1 名與確認段（seq4 §九 必報加）
  ③ 壓力段（合成、非實際 ETF）：0052 早年日線 data/early/daily（3edc0e2206；首日 2006-09-12）、除息 data/early/exright（4 筆，已對官方 TWT49U）
     還原照 early_data.adj_0050 同式（factor ＝ 參考價÷前收；F ＝ 事件日嚴格大於 d 的連乘）× 接點比例（主快照首根 還原÷原始）
     ⇒ 含 0052 的版本從 2006-09-12 起跑（窗首不同，逐字標）；不含 0052 的版本從 2005-02-02（seq3 同）
  持有：A＝00631L（壓力段＝合成正2）；0052 沒有開盤的日子（早年無成交）⇒ 整筆延後（R8，同 seq3）
"""
from __future__ import annotations

import io
import json
import os
import time
from itertools import product

import numpy as np
import pandas as pd

from . import data as D
from . import researchLev2 as L2
from . import researchTri as T

OUT = T.OUT
VERS = [(b, c) for b in ("0050", "0052", "現金") for c in ("0050", "0052")]
LOGF = os.path.join(OUT, "desc0052_run.log")
TAG = "看過三態結果後才加（事後描述；⛔ 不判、不計 N、不取代 seq3）"


def log(m):
    print(m, flush=True)
    with open(LOGF, "a", encoding="utf-8") as f:
        f.write(m + "\n")


def load_0052(G):
    cal = list(G["cal"]); pos = G["pos"]; n = len(cal)
    calm = D.load_calendar(); mstr = [str(x.date()) for x in calm]; off = pos[mstr[0]]
    st = D.load_stock("0052", "twse", calm); df = st.df
    O = np.full(n, np.nan); C = np.full(n, np.nan)
    O[off:off + len(mstr)] = df["open"].to_numpy(float); C[off:off + len(mstr)] = df["close"].to_numpy(float)
    raw = pd.read_csv(os.path.join(D.DATA, "stocks", "0052.csv"), dtype={"date": str}, usecols=["date", "close"]).set_index("date")
    s_ = C[off] / float(raw.loc[mstr[0], "close"])
    sha = T.git("rev-parse", T.EARLY_SHA).strip()
    rows = T.git("grep", "-h", "_0052,", sha, "--", "data/early/daily/")
    cols = ["key", "date", "stock_id", "name", "market", "open", "high", "low", "close", "volume", "amount", "change", "limit",
            "shares", "transactions", "price_basis", "last_price"]
    d = pd.read_csv(io.StringIO(rows), header=None, names=cols, dtype=str)
    d = d[d["stock_id"] == "0052"].copy()
    for k in ("open", "high", "low", "close"):
        d[k] = pd.to_numeric(d[k], errors="coerce")
    bad = (d[["open", "high", "low", "close"]] <= 0).any(axis=1)
    d.loc[bad, ["open", "high", "low", "close"]] = np.nan
    d = d.sort_values("date").drop_duplicates("date")
    d = d[(d["date"] < mstr[0]) & d["close"].notna()].reset_index(drop=True)
    ex = T.git("grep", "-h", ",0052,", sha, "--", "data/early/exright/")
    e = pd.read_csv(io.StringIO(ex), header=None, names=["date", "stock_id", "pre_close", "ref_price", "value", "kind", "open_base",
                                                         "limit_up", "limit_down", "ex_div_ref"], dtype={"date": str, "stock_id": str})
    e = e[e["stock_id"] == "0052"].sort_values("date").reset_index(drop=True)
    f = e["ref_price"].astype(float).to_numpy() / e["pre_close"].astype(float).to_numpy()
    evd = e["date"].to_numpy()
    F = np.array([np.prod(f[evd > x]) for x in d["date"].to_numpy()]) * s_
    for x, o_, c_ in zip(d["date"], d["open"].to_numpy(float) * F, d["close"].to_numpy(float) * F):
        O[pos[x]] = o_; C[pos[x]] = c_
    first = d["date"].iloc[0]; i0 = pos[first]; i1 = pos["2014-12-31"]
    have = set(d["date"])
    miss = [cal[i] for i in range(i0, i1 + 1) if cal[i] not in have]
    # 除息 pre_close 對前一個有成交日收盤
    raw_early = dict(zip(d["date"], d["close"]))
    pc = []
    for r in e.itertuples():
        prevd = max(x for x in have if x < r.date)
        pc.append(float(r.pre_close) - float(raw_early[prevd]))
    # 跳動（早年漲跌幅 7%；相鄰有成交日還原收盤比，超出 7%＋1% 列出）
    cc = C[i0:i1 + 1]; idx = np.flatnonzero(np.isfinite(cc)); q = cc[idx[1:]] / cc[idx[:-1]]
    jumps = [(cal[i0 + idx[k + 1]], float(q[k]), int(idx[k + 1] - idx[k])) for k in np.flatnonzero((q > 1.08) | (q < 0.92))]
    info = {"early_sha": sha, "0052 早年首日": first, "早年有效收盤列": len(d), "早年窗內交易日": i1 - i0 + 1, "早年無成交日（列在、收盤空）": len(miss),
            "早年除息": e[["date", "pre_close", "ref_price", "value"]].to_dict("records"), "除息 pre_close − 前一成交日收盤": pc,
            "接點比例 s": float(s_), "早年跳動超限（>8%）": jumps}
    return O, pd.Series(C).ffill().to_numpy(), info


def W6(st, b, c):
    """assets (0050, 0052, LEV)。"""
    W = np.zeros((len(st), 3))
    W[st == 0, 2] = 1.0
    if b != "現金":
        W[st == 1, 0 if b == "0050" else 1] = 1.0
    W[st == 2, 0 if c == "0050" else 1] = 1.0
    return W


def main():
    os.makedirs(OUT, exist_ok=True); open(LOGF, "w").close()
    log(f"===== researchTri_0052 {pd.Timestamp.now(tz='Asia/Taipei'):%Y-%m-%d %H:%M}（台北）｜{TAG} =====")
    G = T.load_all(); cal = G["cal"]; N = len(cal)
    S, first, _ = T.signals(G); s0 = max(first.values())
    O52, C52, info = load_0052(G)
    log(f"[0052 早年] {json.dumps(info, ensure_ascii=False, default=str)}")
    b50 = pd.Series(G["C"]["0050"]).ffill().to_numpy()
    Oa = {"0050": G["O"]["0050"], "0052": O52, "LEV": G["O"]["00631L"]}
    Ca = {"0050": b50, "0052": C52, "LEV": pd.Series(G["C"]["00631L"]).ffill().to_numpy()}
    e0, e1 = G["pos"][T.EXP[0]], G["pos"][T.EXP[1]]; c0, c1 = G["pos"][T.CONF[0]], G["pos"][T.CONF[1]]
    SEG = {"探索": (e0, e1), "確認": (c0, c1)}

    def bperf(i0, i1):
        seg = b50[i0:i1 + 1]; c, m = L2.R13.window_stats(seg / seg[0], 0, len(seg), 0, len(seg)); return float(c), float(m)
    B = {k: bperf(*v) for k, v in SEG.items()}
    body = json.load(open(os.path.join(OUT, "body_summary.json"), encoding="utf-8"))
    PH = {k: body["純抱00631L"][k]["年化"] for k in SEG}

    def run(W, i0, i1, oa=Oa, ca=Ca):
        n = i1 - i0 + 1
        return L2.engine(("0050", "0052", "LEV"), W[i0:i1 + 1], np.zeros(n, bool), i0, oa, ca)

    # ① W4×P3×U4 × 6 版
    st = T.machine(S, "W4", "P3", "U4", s0, N)
    rows = []
    for (b, c), (sg, (i0, i1)) in product(VERS, SEG.items()):
        r = run(W6(st, b, c), i0, i1); x = T.seg_stats(r, st[i0:i1 + 1], i1 - i0 + 1)
        row = {"標": TAG, "段": sg, "B態": b, "C態": c, **{k: x[k] for k in ("年化", "回落", "比值", "每年轉換", "成交次數", "每年成本", "R8延後")},
               "對0050（描述）": L2.label(x["年化"], x["回落"], *B[sg]), "年化>純抱00631L": x["年化"] > PH[sg]}
        if sg == "確認":
            ny = G["pos"]["2022-12-30"] - c0 + 1; p_ = np.r_[1.0, r["eq"][:ny]]
            row["2022谷底（100萬）"] = float(p_.min() * 1e6); row["2022-12-30（100萬）"] = float(r["eq"][ny - 1] * 1e6)
        rows.append(row)
    six = pd.DataFrame(rows); six.to_csv(os.path.join(OUT, "desc0052_six.csv"), index=False, encoding="utf-8")
    log("[① W4×P3×U4 × 6 版]\n" + six.drop(columns=["標"]).to_string())
    # 閘：B現金／C0050 版 ＝ seq3 挑中那格；B0050／C0050 ＝ seq3 的 B0050 格
    bc = pd.read_csv(os.path.join(OUT, "body_cells.csv"))
    g = {}
    for (b, c), key in ((("現金", "0050"), "Bcash"), (("0050", "0050"), "B0050")):
        for sg in SEG:
            ref = bc[(bc["段"] == sg) & (bc["轉弱"] == "W4") & (bc["跌深"] == "P3") & (bc["反彈"] == "U4") & (bc["B態"] == key)].iloc[0]
            mine = six[(six["段"] == sg) & (six["B態"] == b) & (six["C態"] == c)].iloc[0]
            g[f"{b}/{c} {sg}"] = max(abs(mine["年化"] - ref["年化"]), abs(mine["回落"] - ref["回落"]))
    log(f"[閘 對 seq3 body_cells] {g}")
    if max(g.values()) > 1e-12:
        raise SystemExit("⛔ 閘不過")

    # ② 事後：3,360 格
    t0 = time.time(); rows = []; ST = {}
    for (w, _), (p, _), (u, _), (b, c) in product(T.WEAK, T.DEEP, T.UP, VERS):
        if (w, p, u) not in ST:
            ST[(w, p, u)] = T.machine(S, w, p, u, s0, N)
        s_ = ST[(w, p, u)]
        for sg, (i0, i1) in SEG.items():
            r = run(W6(s_, b, c), i0, i1); c_, m_ = L2.perf(r["eq"])
            rows.append({"段": sg, "轉弱": w, "跌深": p, "反彈": u, "B態": b, "C態": c, "年化": c_, "回落": m_, "比值": L2.ratio(c_, m_),
                         "狀態轉換": int(np.sum(s_[i0 + 1:i1 + 1] != s_[i0:i1]))})
    allc = pd.DataFrame(rows); allc.to_csv(os.path.join(OUT, "desc0052_cells.csv"), index=False, encoding="utf-8")
    log(f"[② 3,360 格] {len(allc)} 列 {time.time() - t0:.0f}s")
    ex = allc[allc["段"] == "探索"].reset_index(drop=True); ex["_o"] = range(len(ex))

    def conf(pk):
        return allc[(allc["段"] == "確認") & (allc["轉弱"] == pk["轉弱"]) & (allc["跌深"] == pk["跌深"]) & (allc["反彈"] == pk["反彈"]) & (allc["B態"] == pk["B態"]) & (allc["C態"] == pk["C態"])].iloc[0]

    def rec(nm, pk):
        cf = conf(pk)
        return {"標": "事後", "挑法": nm, "格": f"{pk['轉弱']}×{pk['跌深']}×{pk['反彈']}×B {pk['B態']}×C {pk['C態']}",
                "探索年化": pk["年化"], "探索回落": pk["回落"], "確認年化": cf["年化"], "確認回落": cf["回落"],
                "確認對0050（描述）": L2.label(cf["年化"], cf["回落"], *B["確認"]), "確認年化>純抱00631L": cf["年化"] > PH["確認"]}
    picks = [rec("乙 只看年化（事後）", ex.sort_values(["年化", "狀態轉換", "_o"], ascending=[False, True, True]).iloc[0])]
    q = ex[(ex["年化"] > B["探索"][0]) & (ex["比值"] >= L2.ratio(*B["探索"]))]
    if len(q):
        picks.append(rec("甲 使用者判準（事後）", q.sort_values(["比值", "狀態轉換", "_o"], ascending=[False, True, True]).iloc[0]))
    for b, c in VERS:
        sub = ex[(ex["B態"] == b) & (ex["C態"] == c)]
        picks.append(rec(f"版 B{b}／C{c} 探索第 1 名（事後）", sub.sort_values(["年化", "狀態轉換", "_o"], ascending=[False, True, True]).iloc[0]))
    pk = pd.DataFrame(picks); pk.to_csv(os.path.join(OUT, "desc0052_picks.csv"), index=False, encoding="utf-8")
    log("[② 事後挑]\n" + pk.drop(columns=["標"]).to_string())

    # ③ 壓力段（合成、非實際 ETF）
    o, c = G["O"]["0050"], b50
    Lc = np.full(N, np.nan); Lo = np.full(N, np.nan); Lc[s0 - 1] = 1.0
    for t in range(s0, N):
        Lo[t] = Lc[t - 1] * (1 + 2 * (o[t] / c[t - 1] - 1)) if np.isfinite(o[t]) else np.nan
        Lc[t] = Lc[t - 1] * (1 + 2 * (c[t] / c[t - 1] - 1) - T.FEE)
    Os = dict(Oa, LEV=Lo); Cs = dict(Ca, LEV=Lc)
    hold = np.zeros((N, 3)); hold[:, 2] = 1.0
    h52 = np.zeros((N, 3)); h52[:, 1] = 1.0
    p52 = G["pos"][info["0052 早年首日"]]; pend = G["pos"][T.STRESS_END]
    wins = {"2005-02-02～2014-12-31": (s0, pend), f"{info['0052 早年首日']}～2014-12-31（0052 上市後）": (p52, pend),
            "2008-01～2009-03": (G["pos"][T.P08[0]], G["pos"][T.P08[1]])}
    srows = []
    for wn, (a_, b_) in wins.items():
        objs = [(f"輪動 B{b}／C{c}", W6(st, b, c)) for b, c in VERS if not ("0052" in (b, c) and wn.startswith("2005"))]
        objs += [("純抱合成正2", hold), ("純抱 0052", h52 if not wn.startswith("2005") else None), ("0050", "B")]
        for nm, W in objs:
            if W is None:
                srows.append({"期間": wn, "對象": nm, "註": "無資料（0052 2006-09-12 才上市；⛔ 不拿 0050 代）"}); continue
            if isinstance(W, str):
                eq = b50[a_:b_ + 1] / b50[a_ - 1]; dl = 0
            else:
                r = run(W, a_, b_, Os, Cs); eq = r["eq"]; dl = r["delay"]
            p_ = np.r_[1.0, eq]; pk_ = np.maximum.accumulate(p_); il = int(np.argmin(p_))
            back = None
            if p_.min() < 1.0:
                aft = np.flatnonzero(p_[il:] >= 1.0); back = int(aft[0]) if len(aft) else None
            srows.append({"期間": wn, "對象": nm, "最大跌幅": float(((p_ - pk_) / pk_).min()), "100萬谷底剩": float(p_.min() * 1e6),
                          "谷底日": str(cal[a_ + il - 1]) if il > 0 else "起點", "谷底後回到100萬交易日": back if back is not None else "期間內未回本",
                          "100萬期末": float(eq[-1] * 1e6), "年化": float(eq[-1] ** (T.ANN / len(eq)) - 1), "R8延後": dl})
    stress = pd.DataFrame(srows); stress.to_csv(os.path.join(OUT, "desc0052_stress.csv"), index=False, encoding="utf-8")
    log("[③ 壓力（合成、非實際 ETF）]\n" + stress.to_string())
    json.dump({"標": TAG, "0052早年": info, "閘": g, "0050同窗": B, "純抱00631L年化": PH,
               "必並陳（裁定 seq228）": {"假訊號": "隨便換也有 19.6% 贏 0050、5.4% 贏純抱正2（seq3）", "2008 合成": "−74.00%（seq3 輪動）",
                                   "2005～2014": "整段 4.31%／年，輸 0050（7.59%）與純抱合成正2（9.48%）",
                                   "措辭": "輪動沒有躲掉大空頭；2022～2026 的好成績主要是一直抱正2"}},
              open(os.path.join(OUT, "desc0052_summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    log("[完]")


if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
"""researchYear1M 的獨立查核（⛔ 不 import backtest.researchYear1M）。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchYear1M_check

從逐種子檔 resultsYear1M/seeds.csv.gz 重算：
  C1 窗端點：自己從快照日曆重找（固定窗照信的起訖；滾動窗 ＝ 每月第一個交易日、終點 ＝ 起點＋1 年之前最後一個交易日）
  C2 0050：自己讀快照 0050 還原收盤（data.load_stock，ffill）重算每窗報酬、回落 ⇒ 對 bench_windows.csv
  C3 種子完整：每 (窗, 格, 版本) 恰 200 顆、r ＝ 0..199、seed ＝ 起點＋r；end_value ＝ 1e6×(1＋ret)
  C4 固定窗：期末金額中位、p10／p25／p75／p90（pandas quantile，linear）、回落中位、贏 0050 種子比例 ⇒ 對 fixed_windows.csv
  C5 滾動窗：②③ 期末中位、減 0050、贏種子比例 ⇒ 對 rolling_windows.csv
  C6 三分位：自己排序（0050 一年報酬、同值依起點）、自己切組（n//3，餘數給前面的組）⇒ 每組贏窗比例、平均差、最差一窗 ⇒ 對 rolling_terciles.csv
  C0 日曆最後一天 ＝ 2026-09-24、不含 2026-09-25（中秋休市的假興櫃日檔）
  C7 前緣（加件）：自己重算「沒有別格年化嚴格更高且回落嚴格更淺」⇒ 對 frontier.csv 兩欄前緣旗標；比值式
  C8 與 0050 混（加件）：從 mix_seeds.csv.gz 重算主窗年化／回落／期末中位與 11 窗期末中位 ⇒ 對 mix.csv；固定窗 w＝0 ＝ 0050
  C9 流動性（加件）：從 liq_positions.csv.gz 重算 ADV20 中位／p10、三檔總額的占比中位／p90／＞10% 占比 ⇒ 對 liquidity.csv；
     另抽 50 筆部位自己從日檔重算 ADV20（進場日前最後 20 個有成交日成交金額平均）
輸出 resultsYear1M/check.json
"""
from __future__ import annotations

import json
import os

import numpy as np
import pandas as pd

from backtest import data as D

SHA = "edc6f8002fed8803795e3486ad57db513f7e9f65"
D.DATA = os.path.expanduser(f"~/h2data/{SHA}/data")
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "resultsYear1M")
CAP = 1_000_000.0
SEED0 = {1: 1000, 4: 1000, 7: 1000, 12: 1000, 15: 1000, 16: 1000, 17: 1000,
         2: 7000, 3: 7000, 6: 7000, 9: 7000, 10: 7000, 11: 7000, 13: 7000, 14: 7000,
         0: 102000, 5: 102000, 8: 102000, 18: 99000, 19: 99000, 20: 99000, 21: 99000, 22: 99000, 23: 99000}
TOL = 1e-9
RTP = dict(float_precision="round_trip")


def close(a, b, tol=TOL):
    a = float(a); b = float(b)
    if np.isnan(a) and np.isnan(b):
        return True
    return abs(a - b) <= tol * max(1.0, abs(a), abs(b))


def main():
    res = {}
    cal = D.load_calendar()
    S = pd.read_csv(os.path.join(OUT, "seeds.csv.gz"), **RTP)
    Bw = pd.read_csv(os.path.join(OUT, "bench_windows.csv"), **RTP)
    Fx = pd.read_csv(os.path.join(OUT, "fixed_windows.csv"), **RTP)
    Rw = pd.read_csv(os.path.join(OUT, "rolling_windows.csv"), **RTP)
    Tr = pd.read_csv(os.path.join(OUT, "rolling_terciles.csv"), **RTP)
    W = json.load(open(os.path.join(OUT, "windows.json"), encoding="utf-8"))

    # C1
    pos = {d: i for i, d in enumerate(cal)}
    want = {"F2017": ("2017-03-02", "2018-03-01"), "L1Y": ("2025-09-24", "2026-09-24"), "YTD26": ("2026-01-02", "2026-09-24")}
    for y in range(2018, 2026):
        yy = cal[cal.year == y]
        want[f"Y{y}"] = (str(yy[0].date()), str(yy[-1].date()))
    c1 = {w["key"]: (w["d0"], w["d1"]) == want[w["key"]] and w["w0"] == pos[pd.Timestamp(w["d0"])] and w["w1"] == pos[pd.Timestamp(w["d1"])]
          for w in W["fixed"]}
    mstarts = [cal[cal.to_period("M") == p][0] for p in pd.period_range("2017-03", cal[-1].to_period("M"), freq="M")]
    rw_want = []
    for s in mstarts:
        e = s + pd.DateOffset(years=1)
        if e > cal[-1] + pd.Timedelta(days=1):
            break
        rw_want.append((str(s.date()), str(cal[cal < e][-1].date())))
    rw_got = [(w["d0"], w["d1"]) for w in W["rolling"]]
    res["C1_窗端點"] = {"固定窗": c1, "滾動窗數_本查核": len(rw_want), "滾動窗數_主程式": len(rw_got), "滾動窗全同": rw_want == rw_got,
                     "過": all(c1.values()) and rw_want == rw_got}

    # C2
    b = pd.Series(D.load_stock("0050", "twse", cal).df["close"].to_numpy()).ffill().to_numpy(float)
    bad2 = 0; maxd = 0.0
    wins = {("fixed", w["key"]): w for w in W["fixed"]} | {("rolling", w["key"]): w for w in W["rolling"]}
    b_end = {}
    for row in Bw.itertuples():
        w = wins[(row.kind, row.win)]
        seg = b[w["w0"]:w["w1"] + 1]
        ret = seg[-1] / seg[0] - 1.0
        mdd = float(np.min(seg / np.maximum.accumulate(seg) - 1.0))
        ok = close(ret, row.ret) and close(mdd, row.mdd) and close(CAP * (1 + ret), row.end_value)
        bad2 += int(not ok); maxd = max(maxd, abs(ret - row.ret), abs(mdd - row.mdd))
        b_end[(row.kind, row.win)] = CAP * (1 + ret)
    res["C2_0050"] = {"窗數": len(Bw), "不符": bad2, "最大絕對差": maxd, "過": bad2 == 0}

    # C3
    g = S.groupby(["kind", "win", "cell", "variant"])
    cnt = g.size()
    rs_ok = g["r"].apply(lambda x: sorted(x) == list(range(200)))
    seed_ok = bool((S["seed"] == S["cell"].map(SEED0) + S["r"]).all())
    ev_ok = bool(np.allclose(S["end_value"], CAP * (1 + S["ret"]), rtol=1e-12, atol=0))
    res["C3_種子"] = {"組數": int(len(cnt)), "每組顆數": sorted(set(cnt.tolist())), "r全齊": bool(rs_ok.all()), "seed式": seed_ok,
                    "end_value式": ev_ok, "過": set(cnt.tolist()) == {200} and bool(rs_ok.all()) and seed_ok and ev_ok}

    # C4
    cellnum = lambda s: 0 if s == "門檻B" else int(str(s).lstrip("#"))
    bad4 = []; n4 = 0
    for row in Fx[Fx["臂"] != "①"].itertuples():
        c = cellnum(row.格); v = "mtm" if str(row.版本).startswith("主版") else "eng"
        x = S[(S["kind"] == "fixed") & (S["win"] == row.窗鍵) & (S["cell"] == c) & (S["variant"] == v)]
        ev = x["end_value"]
        mine = {"期末金額_中位": ev.quantile(0.5), "期末金額_p10": ev.quantile(0.10), "期末金額_p25": ev.quantile(0.25),
                "期末金額_p75": ev.quantile(0.75), "期末金額_p90": ev.quantile(0.90), "最大回落_中位": x["mdd"].quantile(0.5),
                "贏0050種子比例": float((ev.to_numpy() > b_end[("fixed", row.窗鍵)]).sum() / len(ev))}
        n4 += 1
        for k, v_ in mine.items():
            if not close(v_, getattr(row, k)):
                bad4.append((row.窗鍵, row.格, v, k, float(v_), float(getattr(row, k))))
    for row in Fx[Fx["臂"] == "①"].itertuples():
        if not close(row.期末金額_中位, b_end[("fixed", row.窗鍵)]):
            bad4.append((row.窗鍵, "0050", "", "期末", 0, 0))
    res["C4_固定窗"] = {"列數": n4, "不符": bad4[:20], "不符數": len(bad4), "過": not bad4}

    # C5
    bad5 = []
    for row in Rw.itertuples():
        be = b_end[("rolling", row.窗鍵)]
        if not close(be, Rw.loc[row.Index, "0050期末"]):
            bad5.append((row.窗鍵, "0050"))
        for c, lab in ((1, "②#1"), (0, "③門檻B")):
            x = S[(S["kind"] == "rolling") & (S["win"] == row.窗鍵) & (S["cell"] == c) & (S["variant"] == "mtm")]["end_value"]
            md = x.quantile(0.5)
            got_md = Rw.loc[row.Index, f"{lab}_期末中位"]; got_d = Rw.loc[row.Index, f"{lab}_減0050"]
            got_w = Rw.loc[row.Index, f"{lab}_贏0050種子比例"]
            if not (close(md, got_md) and close(md - be, got_d, 1e-7) and close((x > be).mean(), got_w)):
                bad5.append((row.窗鍵, lab, float(md), float(got_md)))
    res["C5_滾動窗"] = {"窗數": len(Rw), "不符": bad5[:20], "不符數": len(bad5), "過": not bad5}

    # C6
    d = pd.DataFrame({"起": Rw["起"], "r50": Rw["0050一年報酬"], "d1": Rw["②#1_減0050"], "d0": Rw["③門檻B_減0050"]})
    order = sorted(range(len(d)), key=lambda i: (d.loc[i, "r50"], d.loc[i, "起"]))
    n = len(order); base, rem = divmod(n, 3); sizes = [base + (1 if i < rem else 0) for i in range(3)]
    groups = {}; k = 0
    for name, sz in zip(("低", "中", "高"), sizes):
        groups[name] = order[k:k + sz]; k += sz
    bad6 = []; mine6 = {}
    for name, ix in groups.items():
        gg = d.loc[ix]
        t = Tr[Tr["組"] == name].iloc[0]
        m = {"窗數": len(gg), "0050一年報酬_最低": gg["r50"].min(), "0050一年報酬_最高": gg["r50"].max()}
        for col, lab in (("d1", "②#1"), ("d0", "③門檻B")):
            m[f"{lab}_贏0050窗數比例"] = float((gg[col] > 0).sum() / len(gg))
            m[f"{lab}_平均差（元）"] = float(gg[col].sum() / len(gg))
            m[f"{lab}_最差一窗差（元）"] = float(gg[col].min())
            m[f"{lab}_最差一窗起"] = gg.loc[gg[col].idxmin(), "起"]
        mine6[name] = {k_: (v_ if isinstance(v_, str) else float(v_)) for k_, v_ in m.items()}
        for k_, v_ in m.items():
            tv = t[k_]
            ok = (str(v_) == str(tv)) if isinstance(v_, str) else close(v_, tv, 1e-7)
            if not ok:
                bad6.append((name, k_, v_, tv))
    res["C6_三分位"] = {"組大小": sizes, "本查核": mine6, "不符": bad6, "過": not bad6}
    res["C0_日曆"] = {"最後一天": str(cal[-1].date()), "含2026-09-25": bool((cal == pd.Timestamp("2026-09-25")).any()),
                     "過": str(cal[-1].date()) == "2026-09-24" and not bool((cal == pd.Timestamp("2026-09-25")).any())}

    # C7 前緣：自己重算「沒有別格年化嚴格更高且回落嚴格更淺」
    fp = os.path.join(OUT, "frontier.csv")
    if os.path.exists(fp):
        Fr = pd.read_csv(fp, **RTP)
        bad7 = []
        for col, mask in (("前緣_主窗", Fr["進前緣"] & (Fr["窗"] == "主窗")), ("前緣_含舊窗（窗不同、只供參考）", Fr["進前緣"])):
            sub = Fr[mask]
            for i, q in sub.iterrows():
                dom = bool(((sub["年化中位"] > q["年化中位"]) & (sub["回落中位"] > q["回落中位"])).any())
                if bool(q[col]) == dom:
                    bad7.append((col, q["編號"], q["格"]))
            if (Fr.loc[~mask, col]).any():
                bad7.append((col, "不進前緣的列被標成前緣"))
        rat = bool(np.allclose(Fr["比值"], Fr["年化中位"] / Fr["回落中位"].abs(), equal_nan=True))
        res["C7_前緣"] = {"列數": len(Fr), "主前緣": Fr.loc[Fr["前緣_主窗"], "編號"].tolist(), "不符": bad7, "比值式": rat, "過": not bad7 and rat}

    # C8 與 0050 混：從 mix_seeds 重算中位
    mp = os.path.join(OUT, "mix_seeds.csv.gz")
    if os.path.exists(mp):
        MS = pd.read_csv(mp, **RTP); MX = pd.read_csv(os.path.join(OUT, "mix.csv"), **RTP)
        bad8 = []
        cnt8 = MS.groupby(["arm", "scope", "w"]).size()
        for q in MX.itertuples():
            g = MS[(MS["arm"] == q.臂) & (MS["w"] == q.選股占比w)]
            gm = g[g["scope"] == "主窗"]
            pairs = [(gm["cagr"].quantile(0.5), q.主窗年化_中位), (gm["mdd"].quantile(0.5), q.主窗最大回落_中位),
                     (gm["end_value"].quantile(0.5), q.主窗100萬期末_中位)]
            for key in [w_["key"] for w_ in W["fixed"]]:
                pairs.append((g[g["scope"] == key]["end_value"].quantile(0.5), MX.loc[q.Index, f"{key}_期末中位"]))
            if not all(close(a_, b_) for a_, b_ in pairs):
                bad8.append((q.臂, q.選股占比w))
        w0rows = MS[MS["w"] == 0.0]
        fx0 = w0rows[w0rows["scope"] != "主窗"]
        bmap_f = {k: v for (kk, k), v in b_end.items() if kk == "fixed"}
        d0 = float((fx0["end_value"] / fx0["scope"].map(bmap_f) - 1).abs().max())
        res["C8_混0050"] = {"組數": int(len(cnt8)), "每組顆數": sorted(set(cnt8.tolist())), "不符": bad8,
                           "固定窗w0對0050最大相對差": d0, "過": not bad8 and set(cnt8.tolist()) == {200} and d0 < 1e-9}

    # C9 流動性：從 liq_positions 重算
    lp = os.path.join(OUT, "liq_positions.csv.gz")
    if os.path.exists(lp):
        LP = pd.read_csv(lp, dtype={"sid": str}, **RTP); LQ = pd.read_csv(os.path.join(OUT, "liquidity.csv"), **RTP)
        bad9 = []
        for q in LQ.itertuples():
            a_ = LP.loc[LP["arm"] == q.臂, "adv20"].to_numpy(float); ok = np.isfinite(a_) & (a_ > 0)
            pairs = [(pd.Series(a_[ok]).quantile(0.5), LQ.loc[q.Index, "ADV20_中位（元）"]),
                     (pd.Series(a_[ok]).quantile(0.10), LQ.loc[q.Index, "ADV20_p10（元）"])]
            for T in (1_000_000, 3_000_000, 5_000_000):
                lab = f"{T // 10000}萬"
                pos = T * LQ.loc[q.Index, "選股袖占比"] / LQ.loc[q.Index, "檔數N"]
                rt = pd.Series(pos / a_[ok])
                pairs += [(rt.quantile(0.5), LQ.loc[q.Index, f"{lab}_占ADV20_中位"]), (rt.quantile(0.9), LQ.loc[q.Index, f"{lab}_占ADV20_p90"]),
                          ((rt > 0.10).sum() / len(rt), LQ.loc[q.Index, f"{lab}_超過10%筆數占比"])]
            if not all(close(x_, y_) for x_, y_ in pairs):
                bad9.append(q.臂)
        # ADV20 抽 50 筆自己從日檔重算（最後 20 個有成交日）
        samp = LP.sample(min(50, len(LP)), random_state=1)
        uni = D.load_universe().set_index("stock_id")["market"]
        bad9b = 0
        for q in samp.itertuples():
            st = D.load_stock(q.sid, uni.get(q.sid, "twse"), cal)
            df = st.df.iloc[:int(q.t)]
            am = df.loc[df["traded"].astype(bool) & df["amount"].notna(), "amount"].to_numpy(float)
            v = am[-20:].mean() if len(am) >= 20 else np.nan
            bad9b += int(not close(v, q.adv20))
        res["C9_流動性"] = {"不符": bad9, "ADV20抽查50筆不符": bad9b, "過": not bad9 and bad9b == 0}

    res["全部過"] = all(v["過"] for k, v in res.items() if isinstance(v, dict) and "過" in v)
    json.dump(res, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    for k, v in res.items():
        print(k, v if not isinstance(v, dict) else {kk: vv for kk, vv in v.items() if kk in ("過", "不符數", "不符", "組大小")})


if __name__ == "__main__":
    main()

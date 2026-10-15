# -*- coding: utf-8 -*-
"""大盤大跌後「只能選 1～3 檔」——C+ 中用事前單一規則挑 1／2／3 檔 vs C+ 隨機挑 vs A 0050／B 00631L（描述性初測；⛔ 不計 N、⛔ 不判定、⛔ 不是買賣建議）
回測線計算子代理，2026-10-16。使用者：「只能選1～3檔！」

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchMktDrop_pick

═══ 讀法（寫死於第一次跑之前）═══
 P0 ⛔ 不重跑引擎：逐筆只讀 resultsMktDrop/deep/c_rows.csv（v1 C 全體 28 事件、主出場、成本 0.585%、淨報酬）；
    C+ ＝ C 中 yoy ＞ 0（同 researchMktDrop_yl；候選含買不到的，買不到另計）；
    A 0050、B 00631L、C+ 全買 ＝ v1／yl event_rows 主出場同事件報酬（B 只有 2015 起；早年 0 筆）；C+ 全買另以 c_rows 重算對帳（差 ＞ 1e-6 ⇒ 停）
 P1 規則（只用大跌日收盤以前可得；並列一律按代號升冪穩定排序）：
    R1 成交額最大 ＝ amt20（大跌日前 20 日均成交額，不含當天；c_rows 沒有當天成交額）降冪
    R2 市值最大 ＝ mcap（未還原收盤 × 股數）降冪；缺市值者排除（早年 2006 全缺、2007～2011 部分有 ⇒ 早年多數事件可挑的只剩有股數的）
    R3 營收年增最高 ＝ yoy 降冪
    R4 營收創 24 月新高（hi24 ＝ 1）中 amt20 最大；符合不足 N 檔 ⇒ 只買符合的；0 檔 ⇒ 該事件空手（報酬 0）
    R5 當天跌最深 ＝ 先跌停（dn）、跌停中 amt20 降冪；未跌停者接在後面按當天報酬 ret1 升冪
    R6 前 60 日漲幅最大（ret60p 降冪；缺者排除）；R7 前 60 日漲幅最小（ret60p 升冪；缺者排除）
 P2 報酬 ＝ 選中 N 檔中買得到者的淨報酬等權平均（同 v1：買不到的那檔不進籃）；選中的全部買不到 ⇒ 0（空手）
 P3 隨機 ＝ 每事件從 C+（含買不到）不放回抽 N 檔 2000 次，同 P2 計報酬；種子 default_rng([2026101602, 事件序, N])
    分布 ＝ 段內（事件×抽樣）合併：平均、P10、P50、P90、虧 ＞10% 機率；另：同一抽樣序號 i 的段平均 ⇒ 2000 個段平均 ⇒ 規則段平均在其中的位置
    （p ＝ 隨機段平均 ≥ 規則段平均的比例；只是位置，⛔ 不當檢定，7 規則 × 3 N × 3 段 ＝ 63 格多重比較）
    波動放大 ＝ 段內（事件×抽樣）合併的標準差 ÷ C+ 全買逐事件報酬的標準差
 P4 每事件、每規則 × N 的選中代號與報酬全列（event_picks.csv）
 P5 10/15 前瞻：candidates_20261015.csv 的 C+ 75 檔；amt20／mcap／ret60p／hi24 用 ~/h2data/<sha>/data（load_bars 還原價；營收用 researchExit5 同式）；缺 ⇒「缺」
輸出 backtest/resultsMktDrop/pick/：MktDrop_pick.json、summary.csv、random.csv、event_picks.csv、forward_20261015.csv、run.log
"""
from __future__ import annotations

import json
import os
import sys
import time

import numpy as np
import pandas as pd

REPO = os.path.expanduser("~/tw-p17")
OUT = os.path.join(REPO, "backtest/resultsMktDrop/pick")
CROWS = os.path.join(REPO, "backtest/resultsMktDrop/deep/c_rows.csv")
V1ER = os.path.join(REPO, "backtest/resultsMktDrop/v1/event_rows.csv")
YLER = os.path.join(REPO, "backtest/resultsMktDrop/yl/event_rows.csv.gz")
FWD = os.path.join(REPO, "backtest/forward/mktdrop/candidates_20261015.csv")
SHA = "4b26f6ad1efaf1369422f7e3b87c019a931d7d57"
FDATA = os.path.expanduser(f"~/h2data/{SHA}/data")
NR = 2000
SEED = 2026101602
SEGS = ["2006～2014", "2015～2021", "2022～", "全部"]
RULES = {"R1": "成交額最大（前20日均）", "R2": "市值最大", "R3": "營收年增最高", "R4": "營收創24月新高中成交額最大",
         "R5": "當天跌最深（跌停中成交額最大）", "R6": "前60日漲幅最大（原本最強）", "R7": "前60日漲幅最小（原本最弱）"}
NOTES = ["描述性初測：⛔ 不計 N、⛔ 不判定、⛔ 不是買賣建議",
         "只有 28 個事件（早年 10、2015～2021 7、2022～ 11）；7 規則 × 3 N × 3 段 ＝ 63 格多重比較 ⇒ 規則間差異多半是運氣；p 只是位置、不是檢定",
         "C+ 是看過 deep 拆解之後才切的（事後重切）；規則也是事後列的 ⇒ 任何「看起來較好」只是待驗線索",
         "成交額 ＝ 大跌日前 20 日均成交額（c_rows 無當天成交額）；市值早年 2006 全缺、2007～2011 部分有 ⇒ R2 早年是「有股數者中市值最大」",
         "B 00631L 2014-10 才上市 ⇒ 早年段沒有 B",
         "主出場：加權收盤收復事件前一日收盤 ⇒ 隔天開盤賣（⛔ 不設天數）；成本 0.585% 來回；未含滑價"]
LOG = []


def log(s):
    print(s, flush=True); LOG.append(s)


def order(d: pd.DataFrame, rule: str) -> pd.DataFrame:
    d = d.sort_values("sid", kind="mergesort")
    if rule == "R1":
        return d.sort_values("amt20", ascending=False, kind="mergesort", na_position="last")
    if rule == "R2":
        return d[np.isfinite(d["mcap"])].sort_values("mcap", ascending=False, kind="mergesort")
    if rule == "R3":
        return d.sort_values("yoy", ascending=False, kind="mergesort")
    if rule == "R4":
        return d[d["hi24"] == 1].sort_values("amt20", ascending=False, kind="mergesort", na_position="last")
    if rule == "R5":
        a = d[d["dn"]].sort_values("amt20", ascending=False, kind="mergesort", na_position="last")
        b = d[~d["dn"]].sort_values("ret1", ascending=True, kind="mergesort")
        return pd.concat([a, b])
    if rule == "R6":
        return d[np.isfinite(d["ret60p"])].sort_values("ret60p", ascending=False, kind="mergesort")
    if rule == "R7":
        return d[np.isfinite(d["ret60p"])].sort_values("ret60p", ascending=True, kind="mergesort")
    raise ValueError(rule)


def stats(x):
    x = np.asarray(x, float)
    return {"事件數": len(x), "平均": float(x.mean()), "中位": float(np.median(x)), "勝率": float((x > 0).mean()), "最差": float(x.min()),
            "最好": float(x.max()), "虧＞10%次數": int((x < -0.10).sum()), "標準差": float(x.std(ddof=1)) if len(x) > 1 else np.nan}


def main():
    T0 = time.time()
    os.makedirs(OUT, exist_ok=True)
    C = pd.read_csv(CROWS, dtype={"sid": str})
    C["dn"] = C["dn"].astype(str).str.lower().eq("true"); C["買得到"] = C["買得到"].astype(str).str.lower().eq("true")
    CP = C[C["yoy"] > 0].copy()
    evs = sorted(CP["事件日"].unique()); seg_of = CP.drop_duplicates("事件日").set_index("事件日")["段"].to_dict()
    assert len(evs) == 28, len(evs)
    log(f"[讀檔] c_rows {len(C)} 列；C+ {len(CP)} 列（買不到 {int((~CP['買得到']).sum())}）；事件 {len(evs)}")
    # ── 對照 A／B／C+ 全買 ──
    V = pd.read_csv(V1ER); V = V[(V["出場"] == "主") & (V["定義"] == "q2")]
    Y = pd.read_csv(YLER); Y = Y[Y["r"].isna() | (Y["r"].astype(str) == "") | (Y["r"].astype(str) == "nan")]
    ref = {}
    for ev in evs:
        wn = "早年" if seg_of[ev] == "2006～2014" else "主"
        r = {}
        for cd in ("A", "B"):
            q = V[(V["世界"] == wn) & (V["候選"] == cd) & (V["日期"] == ev)]
            q = q[q["進場"].astype(str).str.lower() == "true"]
            r[cd] = float(q["報酬"].iloc[0]) if len(q) else np.nan
        q = Y[(Y["世界"] == wn) & (Y["候選"] == "C+") & (Y["日期"] == ev)]
        assert len(q) == 1, (ev, len(q))
        r["C+全買"] = float(q["報酬"].iloc[0])
        d = CP[(CP["事件日"] == ev) & CP["買得到"]]
        mine = float(d["淨報酬"].mean())
        assert abs(mine - r["C+全買"]) < 1e-6, (ev, mine, r["C+全買"])
        qa = Y[(Y["世界"] == wn) & (Y["候選"] == "A") & (Y["日期"] == ev)]
        if len(qa) and np.isfinite(r["A"]):
            assert abs(float(qa["報酬"].iloc[0]) - r["A"]) < 1e-6
        ref[ev] = r
    log("[對帳] C+ 全買（c_rows 重算）＝ yl event_rows：28/28 差 ＜ 1e-6；A（v1）＝ A（yl）")
    # ── 規則 ──
    EP = []
    for ev in evs:
        d = CP[CP["事件日"] == ev]
        for rk in RULES:
            o = order(d, rk)
            for N in (1, 2, 3):
                pk = o.head(N)
                nb = pk[pk["買得到"]]
                ret = float(nb["淨報酬"].mean()) if len(nb) else 0.0
                EP.append({"段": seg_of[ev], "事件日": ev, "規則": rk, "N": N, "C+檔數": len(d), "可排序檔數": len(o), "選中": " ".join(pk["sid"]),
                           "選中檔數": len(pk), "買到檔數": len(nb), "空手": len(nb) == 0, "報酬": ret,
                           "選中各檔報酬": " ".join(f"{x:.4f}" if b else "買不到" for x, b in zip(pk["淨報酬"], pk["買得到"]))})
    EP = pd.DataFrame(EP)
    # ── 隨機 ──
    RS = {}   # (ev, N) -> array(NR)
    for i, ev in enumerate(evs):
        d = CP[CP["事件日"] == ev]
        net = np.where(d["買得到"].to_numpy(), d["淨報酬"].to_numpy(float), np.nan); m = len(net)
        for N in (1, 2, 3):
            rng = np.random.default_rng([SEED, i, N])
            ix = np.argsort(rng.random((NR, m)), axis=1)[:, :N]
            v = net[ix]
            fin = np.isfinite(v); cnt = fin.sum(axis=1)
            RS[(ev, N)] = np.where(cnt > 0, np.where(fin, v, 0.0).sum(axis=1) / np.maximum(cnt, 1), 0.0)
    # ── 彙總 ──
    SUM = []; RND = []
    for sg in SEGS:
        es = [e for e in evs if sg == "全部" or seg_of[e] == sg]
        cpa = np.array([ref[e]["C+全買"] for e in es]); sd_cp = float(cpa.std(ddof=1))
        for cd in ("A", "B", "C+全買"):
            x = np.array([ref[e][cd] for e in es]); x = x[np.isfinite(x)]
            if len(x) == 0:
                SUM.append({"段": sg, "方法": cd, "N": "", "事件數": 0}); continue
            s = stats(x)
            SUM.append({"段": sg, "方法": cd, "名稱": {"A": "0050", "B": "00631L", "C+全買": "C+ 全部等權"}[cd], "N": "", **s,
                        "標準差÷C+全買": s["標準差"] / sd_cp})
        for N in (1, 2, 3):
            M = np.stack([RS[(e, N)] for e in es])          # 事件 × NR
            segavg = M.mean(axis=0); flat = M.ravel()
            sd_r = float(flat.std(ddof=1))
            RND.append({"段": sg, "N": N, "事件數": len(es), "抽樣": NR, "平均": float(flat.mean()), "P10": float(np.quantile(flat, .1)),
                        "P50": float(np.quantile(flat, .5)), "P90": float(np.quantile(flat, .9)), "勝率": float((flat > 0).mean()),
                        "虧＞10%機率": float((flat < -0.10).mean()), "虧＞10%預期次數": float((M < -0.10).sum(axis=0).mean()),
                        "段平均P10": float(np.quantile(segavg, .1)), "段平均P50": float(np.quantile(segavg, .5)), "段平均P90": float(np.quantile(segavg, .9)),
                        "最差一次平均（每輪段內最差）": float(M.min(axis=0).mean()),
                        "標準差（事件×抽樣合併）": sd_r, "C+全買逐事件標準差": sd_cp, "波動放大倍數": sd_r / sd_cp})
            SUM.append({"段": sg, "方法": "隨機", "名稱": f"C+ 隨機挑 {N} 檔（{NR} 次）", "N": N, "事件數": len(es), "平均": float(flat.mean()),
                        "中位": float(np.quantile(flat, .5)), "勝率": float((flat > 0).mean()), "最差": float(M.min(axis=0).mean()),
                        "最好": float(M.max(axis=0).mean()), "虧＞10%次數": float((M < -0.10).sum(axis=0).mean()), "標準差": sd_r, "標準差÷C+全買": sd_r / sd_cp,
                        "隨機段平均P10": float(np.quantile(segavg, .1)), "隨機段平均P90": float(np.quantile(segavg, .9))})
            for rk in RULES:
                q = EP[(EP["規則"] == rk) & (EP["N"] == N) & (EP["事件日"].isin(es))].set_index("事件日").loc[es]
                x = q["報酬"].to_numpy(float); s = stats(x)
                SUM.append({"段": sg, "方法": rk, "名稱": RULES[rk], "N": N, **s, "空手事件數": int(q["空手"].sum()),
                            "選中不足N事件數": int((q["選中檔數"] < N).sum()), "標準差÷C+全買": s["標準差"] / sd_cp,
                            "隨機段平均P10": float(np.quantile(segavg, .1)), "隨機段平均P90": float(np.quantile(segavg, .9)),
                            "p（隨機段平均≥規則）": float((segavg >= s["平均"]).mean()),
                            "勝過C+全買事件數": int((x > cpa).sum()), "勝過A事件數": int(sum(1 for e, v in zip(es, x) if np.isfinite(ref[e]["A"]) and v > ref[e]["A"]))})
    SUM = pd.DataFrame(SUM); RND = pd.DataFrame(RND)
    SUM.to_csv(os.path.join(OUT, "summary.csv"), index=False, float_format="%.6g", encoding="utf-8")
    RND.to_csv(os.path.join(OUT, "random.csv"), index=False, float_format="%.6g", encoding="utf-8")
    EP.to_csv(os.path.join(OUT, "event_picks.csv"), index=False, float_format="%.6g", encoding="utf-8")
    pd.set_option("display.width", 250); pd.set_option("display.max_rows", 500); pd.set_option("display.max_columns", 30)
    log("[彙總]\n" + SUM[["段", "方法", "N", "事件數", "平均", "中位", "勝率", "最差", "虧＞10%次數", "標準差÷C+全買", "p（隨機段平均≥規則）", "空手事件數"]].to_string(index=False, float_format=lambda v: f"{v:.3f}"))
    log("[隨機]\n" + RND.to_string(index=False, float_format=lambda v: f"{v:.3f}"))
    # ── 10/15 前瞻 ──
    FW = forward()
    S = {"程式": "backtest/researchMktDrop_pick.py", "時間": pd.Timestamp.now(tz="Asia/Taipei").strftime("%Y-%m-%d %H:%M"), "讀法": __doc__, "註": NOTES,
         "規則": RULES, "summary": SUM.replace({np.nan: None}).to_dict("records"), "random": RND.replace({np.nan: None}).to_dict("records"),
         "forward_20261015": FW, "耗時秒": round(time.time() - T0, 1)}
    with open(os.path.join(OUT, "MktDrop_pick.json"), "w", encoding="utf-8") as f:
        json.dump(S, f, ensure_ascii=False, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o))
    with open(os.path.join(OUT, "run.log"), "w", encoding="utf-8") as f:
        f.write("\n".join(LOG) + "\n")


def forward():
    sys.path.insert(0, REPO)
    from backtest import data as D
    from backtest import research11 as R
    from backtest import researchExit5 as EX5
    D.DATA = FDATA
    cal = D.load_calendar(); n0 = len(cal); TP = n0 - 1
    assert str(cal[-1].date()) == "2026-10-15", cal[-1]
    F = pd.read_csv(FWD, dtype={"代號": str}, encoding="utf-8-sig")
    F = F[F["候選"] == "C+"].reset_index(drop=True)
    mk = pd.read_csv(os.path.join(FDATA, "meta", "stocks.csv"), dtype=str).drop_duplicates("stock_id", keep="last").set_index("stock_id")["market"].to_dict()
    rev, rly, _ = EX5.load_revenue(FDATA); AV = EX5.avail_pos(list(rev.index), cal)
    rows = []
    for sid, nm, r1, yoy, dn in zip(F["代號"], F["名稱"], F["當日報酬"], F["年增"], F["是否跌停"]):
        f = {"sid": sid, "名稱": nm, "ret1": float(r1), "yoy": float(yoy), "dn": str(dn) == "是", "amt20": np.nan, "mcap": np.nan, "ret60p": np.nan, "hi24": np.nan}
        B = R.load_bars(sid, mk.get(sid, "twse"), cal)
        if B is not None:
            idx = B["idx"].astype(np.int64); nb = len(idx); k = nb - 1
            if idx[k] == TP:
                c = np.asarray(B["c"], float); amt = np.asarray(B["amt"], float); rc = np.asarray(B["rc"], float)
                bad = np.asarray(np.asarray(B["next_bad"])[:nb] == np.arange(nb), bool)
                if k >= 20:
                    f["amt20"] = float(np.mean(amt[k - 20:k]))
                if k >= 61 and not bad[k - 60:k].any():
                    f["ret60p"] = float(c[k - 1] / c[k - 61] - 1)
                raw = pd.read_csv(os.path.join(FDATA, "stocks", f"{sid}.csv"), dtype={"date": str}, usecols=["date", "shares"])
                sh = pd.to_numeric(raw["shares"], errors="coerce").ffill().to_numpy(float)
                if len(sh) and np.isfinite(sh[-1]) and sh[-1] > 0:
                    f["mcap"] = float(rc[k] * sh[-1])
        ev = EX5.rev_events(sid, rev, rly, AV, n0)
        evk = [e for e in ev if e[0] <= TP]
        if evk:
            f["hi24"] = np.nan if evk[-1][2] is None else float(evk[-1][2])
            f["yoy_chk"] = evk[-1][1]
        rows.append(f)
    d = pd.DataFrame(rows)
    mx = float(np.nanmax(np.abs(d["yoy"] - d["yoy_chk"]))) if "yoy_chk" in d else np.nan
    log(f"[10/15] C+ {len(d)} 檔；缺：amt20 {int(d['amt20'].isna().sum())}、mcap {int(d['mcap'].isna().sum())}、ret60p {int(d['ret60p'].isna().sum())}、hi24 {int(d['hi24'].isna().sum())}；年增對 csv 最大差 {mx:.2e}")
    d["買得到"] = True; d["淨報酬"] = np.nan
    out = {}; L = []
    for rk in RULES:
        o = order(d, rk)
        for N in (1, 2, 3):
            pk = o.head(N)
            out[f"{rk}_N{N}"] = [f"{s} {n}" for s, n in zip(pk["sid"], pk["名稱"])]
        for j, (_, r) in enumerate(o.head(3).iterrows()):
            L.append({"規則": rk, "規則名": RULES[rk], "名次": j + 1, "代號": r["sid"], "名稱": r["名稱"], "當日報酬": r["ret1"], "跌停": r["dn"],
                      "營收年增": r["yoy"], "創24月新高": ("缺" if not np.isfinite(r["hi24"]) else ("是" if r["hi24"] > 0.5 else "否")),
                      "前20日均成交額（億）": (r["amt20"] / 1e8 if np.isfinite(r["amt20"]) else "缺"), "市值（億）": (r["mcap"] / 1e8 if np.isfinite(r["mcap"]) else "缺"),
                      "前60日漲幅": (r["ret60p"] if np.isfinite(r["ret60p"]) else "缺")})
        if len(o) < 3:
            L.append({"規則": rk, "規則名": RULES[rk], "名次": len(o) + 1, "代號": "缺", "名稱": f"符合只有 {len(o)} 檔"})
    L = pd.DataFrame(L)
    L.to_csv(os.path.join(OUT, "forward_20261015.csv"), index=False, float_format="%.6g", encoding="utf-8")
    d.drop(columns=["買得到", "淨報酬"]).to_csv(os.path.join(OUT, "forward_20261015_features.csv"), index=False, float_format="%.6g", encoding="utf-8")
    log("[10/15 各規則前 3]\n" + L.to_string(index=False, float_format=lambda v: f"{v:.3f}"))
    log(f"[10/15] hi24＝1 檔數 {int((d['hi24'] == 1).sum())}；跌停 {int(d['dn'].sum())}")
    return {"選中": out, "表": L.replace({np.nan: None}).to_dict("records")}


if __name__ == "__main__":
    main()

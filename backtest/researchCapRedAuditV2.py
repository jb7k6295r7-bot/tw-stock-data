# -*- coding: utf-8 -*-
"""減資查核 v2：早年減資因子接進還原鏈後，重建 earlydata → stitch → s5work，重跑 researchCapRedAudit 的早年段（stitch 版面）分類。
回測線計算子代理，2026-10-11。依據：資料庫線 2026-10-11 20:32「早年減資因子交件：上市2004～2010偵測176筆」§四。

⛔ 不覆蓋既有 s5work、resultsSurge5、resultsCapRedAudit 既有檔；⛔ 不重跑任何已結案研究（只重建 s5 名單底表＋本查核的分類）。
   新輸出：~/earlydata/950ad26e12/reduce_v2/data、~/evtdata/stitch_950ad26e12rv2_b53f5540a8/data、~/s5work_rv2、~/capred_work/v2、backtest/resultsCapRedAudit/v2/

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchCapRedAuditV2 gate            # 既有 variant 逐位元閘（舊程式 vs 新程式）
    ...                                                          -m backtest.researchCapRedAuditV2 early           # 產 reduce_v2 早年版面
    ...                                                          -m backtest.researchCapRedAuditV2 s5build [--procs 3]   # 接合＋s5 建表（S5WORK＝~/s5work_rv2）
    ...                                                          -m backtest.researchCapRedAuditV2 scan [--procs 3]      # researchCapRedAudit._one 掃新接合版面
    ...                                                          -m backtest.researchCapRedAuditV2 report          # 分類＋s5 假飆股＋網格比較 ⇒ resultsCapRedAudit/v2/

讀法：與 researchCapRedAudit Z1～Z10 相同（直接呼叫其 _one／classify／cross／load_official／load_news）；另加三個標籤（只描述、不改原分類順序）：
  T1 資料庫未解釋22筆 ＝ twse_jump_unexplained_2004_2010.csv 的 date ∈ (p, t]
  T2 上市偵測176     ＝ twse_reduce_detected_2004_2010.csv 的 date ∈ (p, t]
  T3 上櫃偵測148     ＝ otc_reduce_detected_2007_2012.csv（shares_down＝1 ∧ exright_in_gap＝0）resume_day ∈ (p, t]
s5 假飆股（同 researchCapRedAudit Q4b）：網格事件列 (d, P] 內跨過「沒解釋、價格規則沒擋、上跳」的跳動 ⇒ (1＋M)÷Π跳動比 − 1 ＜ g。
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import time
from argparse import Namespace
from multiprocessing import Pool

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import early_data as E  # noqa: E402

H = os.path.expanduser
SHA950 = "950ad26e1293592457ec28194f0c5eaebfd3e53b"
EARLY_V2 = H("~/earlydata/950ad26e12/reduce_v2/data")
ST_V2 = H("~/evtdata/stitch_950ad26e12rv2_b53f5540a8/data")
WORK5_V2 = H("~/s5work_rv2")
WORK5_OLD = H("~/s5work")
CRW = H("~/capred_work/v2")
CRW_OLD = H("~/capred_work")
OUT = "backtest/resultsCapRedAudit/v2"
GS5 = (0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0, 7.0, 10.0)


def log(m):
    print(f"[{time.strftime('%H:%M:%S')}] {m}", flush=True)


def tree_hash(root):
    """data/ 樹：排序後的 (相對路徑, sha256) 清單再 sha256。"""
    h = hashlib.sha256(); n = 0
    for dp, dn, fn in os.walk(root):
        dn.sort()
        for f in sorted(fn):
            p = os.path.join(dp, f)
            h.update(os.path.relpath(p, root).encode()); h.update(hashlib.sha256(open(p, "rb").read()).digest()); n += 1
    return h.hexdigest(), n


# ═════════════ gate：既有 variant（main、restore）舊程式 vs 新程式逐位元 ═════════════
def gate():
    g = os.path.join(CRW, "gate"); os.makedirs(g, exist_ok=True)
    old_py = os.path.join(g, "early_data_old.py")
    head = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
    open(old_py, "wb").write(subprocess.run(["git", "show", "HEAD:backtest/early_data.py"], capture_output=True, check=True).stdout)
    spec = importlib.util.spec_from_file_location("early_data_old", old_py); OLD = importlib.util.module_from_spec(spec); spec.loader.exec_module(OLD)
    src = E.snap_dir(SHA950)
    res = {"HEAD": head, "舊程式": f"git show HEAD:backtest/early_data.py（{head[:10]}）", "新程式": "工作樹 backtest/early_data.py"}
    for name, mod in (("old", OLD), ("new", E)):
        root = os.path.join(g, name)
        sd = os.path.join(root, SHA950[:10]); os.makedirs(sd, exist_ok=True)
        for f in ("raw", "raw_manifest.json", "daily_all.pkl"):
            if not os.path.exists(os.path.join(sd, f)):
                os.symlink(os.path.join(src, f), os.path.join(sd, f))
        mod.ROOT = root
        for v in ("main", "restore"):
            st = mod.body_build(SHA950, v, log)
            th, n = tree_hash(os.path.join(sd, v, "data"))
            stc = {k: x for k, x in st.items() if k != "data"}
            res[f"{name}_{v}"] = {"data 樹 sha256": th, "檔數": n, "STATUS（去 data 路徑）sha256": hashlib.sha256(json.dumps(stc, ensure_ascii=False, sort_keys=True).encode()).hexdigest(),
                                 "adj 事件": st["adj 事件"]}
            log(f"[gate] {name} {v} {th[:16]} {n} 檔")
    E.ROOT = H("~/earlydata")
    prod = tree_hash(os.path.join(src, "main", "data"))
    res["正式 ~/earlydata/950ad26e12/main/data"] = {"data 樹 sha256": prod[0], "檔數": prod[1]}
    res["閘"] = {"main 舊＝新": res["old_main"]["data 樹 sha256"] == res["new_main"]["data 樹 sha256"] and res["old_main"]["STATUS（去 data 路徑）sha256"] == res["new_main"]["STATUS（去 data 路徑）sha256"],
                "restore 舊＝新": res["old_restore"]["data 樹 sha256"] == res["new_restore"]["data 樹 sha256"] and res["old_restore"]["STATUS（去 data 路徑）sha256"] == res["new_restore"]["STATUS（去 data 路徑）sha256"],
                "新 main ＝ 正式 950ad26e12/main": res["new_main"]["data 樹 sha256"] == prod[0]}
    os.makedirs(OUT, exist_ok=True)
    json.dump(res, open(os.path.join(OUT, "gate.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps(res["閘"], ensure_ascii=False))
    if not all(res["閘"].values()):
        raise SystemExit("⛔ 閘不過")


# ═════════════ early：reduce_v2 版面 ═════════════
def early():
    tj = os.path.join(E.snap_dir(SHA950), "transferred.json")
    before = hashlib.sha256(open(tj, "rb").read()).hexdigest() if os.path.exists(tj) else None
    st = E.body_build(SHA950, "reduce_v2", log)
    after = hashlib.sha256(open(tj, "rb").read()).hexdigest()
    assert before is None or before == after, "⛔ transferred.json 內容變了"
    print(json.dumps({k: st[k] for k in ("adj 事件", "adj 檔數", "reduce_ext")}, ensure_ascii=False, indent=1))


# ═════════════ s5build：接合＋建表（同 researchSurge5 build，只換路徑）═════════════
def _s5(work=WORK5_V2, st=ST_V2, early_=EARLY_V2):
    from backtest import researchSurge5 as S5
    S5.EARLY, S5.ST, S5.WORK = early_, st, work
    return S5


def s5build(procs):
    S5 = _s5()
    T0 = time.time()
    S5.build(Namespace(procs=procs, limit=0), lambda m: log(f"[{time.time() - T0:6.0f}s] {m}"))
    json.dump({"early": EARLY_V2, "early_variant": "reduce_v2", "early_sha": SHA950, "reduce_ext_sha": E.REDUCE_EXT_SHA, "main": S5.MAIN, "stitch": ST_V2},
              open(os.path.join(WORK5_V2, "variant.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)


# ═════════════ scan：researchCapRedAudit._one 掃新接合版面 ═════════════
def scan(procs):
    from backtest import researchCapRedAudit as CR
    from backtest import data as D
    os.makedirs(CRW, exist_ok=True)
    T0 = time.time()
    D.DATA = ST_V2
    cal = D.load_calendar(); uni = D.load_universe()
    args = list(zip(uni["stock_id"], uni["market"]))
    with Pool(procs, initializer=CR._init, initargs=(ST_V2,)) as P:
        res = P.map(CR._one, args, chunksize=8)
    R = pd.DataFrame([r for rr in res for r in rr]); R.insert(0, "world", "stitch_v2")
    R.to_pickle(os.path.join(CRW, "scan_stitch_v2.pkl"))
    meta = {"data": ST_V2, "日曆": [str(cal[0].date()), str(cal[-1].date()), len(cal)], "母體檔數": len(args), "列": len(R), "秒": round(time.time() - T0)}
    json.dump(meta, open(os.path.join(CRW, "scan_meta.json"), "w"), ensure_ascii=False, indent=1)
    log(f"[scan] {meta}")


# ═════════════ report ═════════════
def ext_tags():
    d = E.reduce_ext_dir(SHA950, E.REDUCE_EXT_SHA)
    u = pd.read_csv(os.path.join(d, "twse_jump_unexplained_2004_2010.csv"), dtype=str)
    t = pd.read_csv(os.path.join(d, "twse_reduce_detected_2004_2010.csv"), dtype=str)
    o = pd.read_csv(os.path.join(d, "otc_reduce_detected_2007_2012.csv"), dtype=str)
    o = o[(o["shares_down"] == "1") & (o["exright_in_gap"] == "0")]

    def todict(s, dd):
        out = {}
        for a, b in zip(s, dd):
            out.setdefault(a, []).append(np.datetime64(b))
        return {k: np.sort(np.array(v, dtype="datetime64[D]")) for k, v in out.items()}
    return {"資料庫未解釋22筆": todict(u["stock_id"], u["date"]), "上市偵測176": todict(t["stock_id"], t["date"]),
            "上櫃偵測148": todict(o["stock_id"], o["resume_day"])}, {"未解釋": len(u), "上市偵測": len(t), "上櫃偵測148": len(o)}


def tag_rows(R, tags):
    out = []
    for s, p, t in zip(R["sid"], R["p_date"], R["t_date"]):
        p = np.datetime64(p); t = np.datetime64(t); hit = []
        for k, dct in tags.items():
            a = dct.get(s)
            if a is not None and ((a > p) & (a <= t)).any():
                hit.append(k)
        out.append("+".join(hit))
    return out


def s5_cross(work, J, calS, CR):
    s5 = np.load(os.path.join(work, "events.npz"))
    uni5 = pd.read_csv(os.path.join(work, "uni.csv"), dtype=str)
    EP = pd.DataFrame({"cell": s5["cell"], "s": s5["s"], "d": s5["d"], "P": s5["P"], "M": s5["M"]})
    EP["sid"] = uni5["stock_id"].to_numpy()[EP["s"].to_numpy()]
    EP["g"] = np.array(GS5)[EP["cell"].to_numpy() % len(GS5)]
    EP["per"] = np.where(calS[EP["d"].to_numpy()] < pd.Timestamp("2015-01-01"), "2004-2014", "2015-")
    hits = CR.cross(EP["sid"].to_numpy(), EP["d"].to_numpy(), EP["P"].to_numpy(), J, len(calS))
    H5 = pd.DataFrame(hits, columns=["i", "j"])
    H5["ratio"] = J.loc[H5["j"], "adj_ratio"].to_numpy(); H5["red"] = J.loc[H5["j"], "cls"].isin(CR.RED).to_numpy()
    H5["strong"] = J.loc[H5["j"], "cls"].isin(CR.STRONG).to_numpy()
    H5["cls"] = J.loc[H5["j"], "cls"].to_numpy(); H5["tag"] = J.loc[H5["j"], "tag"].to_numpy()
    agg = H5.groupby("i").agg(prod=("ratio", "prod"), red=("red", "any"), strong=("strong", "any"),
                              cls=("cls", lambda x: "+".join(sorted(set(x)))), tag=("tag", lambda x: "+".join(sorted({z for z in x if z}))))
    agg = agg.join(EP[["M", "g", "per", "sid", "cell", "d"]])
    agg["fake"] = (1 + agg["M"]) / agg["prod"] - 1 < agg["g"]
    r = {"網格事件列": int(len(EP))}
    for per in ("2004-2014", "2015-"):
        a = agg[agg["per"] == per]; n = int((EP["per"] == per).sum())
        r[per] = {"網格事件列": n, "網格不重複(s,d)": int(EP[EP["per"] == per].drop_duplicates(["sid", "d"]).shape[0]),
                  "跨過沒擋上跳": int(len(a)), "其中減資類跳動": int(a["red"].sum()),
                  "扣掉跳動後低於門檻（假飆股）": int(a["fake"].sum()), "假飆股比例（全部類）": float(a["fake"].sum() / n) if n else np.nan,
                  "假飆股｜減資類（含新聞旁證）": int((a["fake"] & a["red"]).sum()),
                  "跨過｜強證據減資（官方、偵測、股數減少）": int(a["strong"].sum()), "假飆股｜強證據減資": int((a["fake"] & a["strong"]).sum()),
                  "假飆股比例｜強證據減資": float((a["fake"] & a["strong"]).sum() / n) if n else np.nan,
                  "假飆股｜強證據減資｜檔數": int(a.loc[a["fake"] & a["strong"], "sid"].nunique()),
                  "假飆股｜強證據減資｜不重複(s,d)": int(a.loc[a["fake"] & a["strong"]].drop_duplicates(["sid", "d"]).shape[0]),
                  "假飆股｜不重複(s,d)": int(a.loc[a["fake"]].drop_duplicates(["sid", "d"]).shape[0]),
                  "涉及檔數": int(a["sid"].nunique()), "假飆股涉及檔數": int(a.loc[a["fake"], "sid"].nunique())}
    return r, agg, EP


def grid_early(work):
    """researchSurge5_desc 的 事件／定義域股日／比例／兩個最大漲幅中位（只早年段；同式重寫）。"""
    S5 = _s5(work=work, st=(ST_V2 if work == WORK5_V2 else H("~/evtdata/stitch_950ad26e12_b53f5540a8/data")))
    uni, cal, mon, segd, Ev = S5.load_all()
    bar = np.load(os.path.join(work, "bar.npy")); hdef = np.load(os.path.join(work, "hdef.npy"))
    dm = segd["早年"]; rows = bar & dm[None, :]
    h = np.bincount(hdef[rows].astype(np.int64), minlength=252); ge = np.cumsum(h[::-1])[::-1]
    ec, ed = Ev["cell"].astype(int), Ev["d"].astype(int); ine = dm[ed]
    G = []
    for c in range(S5.NC):
        hi, gi = divmod(c, len(S5.GS)); Hh, g = S5.HS[hi], S5.GS[gi]
        k = np.flatnonzero((ec == c) & ine); dc = int(ge[Hh])
        G.append({"格": S5.cell_name(c), "H": Hh, "g": g, "事件": len(k), "定義域股日": dc, "比例": len(k) / dc if dc else np.nan,
                  "最大漲幅中位（H內）": float(np.median(Ev["M"][k])) if len(k) else np.nan,
                  "最大漲幅中位（不設H，到回落30%前）": float(np.median(Ev["ps_g"][k])) if len(k) else np.nan})
    uq = pd.DataFrame({"s": Ev["s"][ine], "d": ed[ine]}).drop_duplicates().shape[0]
    return pd.DataFrame(G), {"早年股日": int(rows.sum()), "早年事件列": int(ine.sum()), "早年不重複(s,d)": int(uq)}


def report():
    from backtest import researchCapRedAudit as CR
    from backtest import data as D
    os.makedirs(OUT, exist_ok=True)
    news = CR.load_news(); off, det, ocnt = CR.load_official()
    tags, tcnt = ext_tags()
    S = {"old": pd.read_pickle(os.path.join(CRW_OLD, "scan_stitch.pkl")), "v2": pd.read_pickle(os.path.join(CRW, "scan_stitch_v2.pkl"))}
    for w, R in S.items():
        R["period"] = np.where(R["t_date"] < "2015-01-01", "2004-2014", "2015-")
        u = R["type"] == "unexplained"
        R.loc[u, "cls"] = CR.classify(R[u], off, det, news); R.loc[~u, "cls"] = "adj 減資事件"
        R["tag"] = tag_rows(R, tags)
    SUM = {"讀法": "見本檔 docstring（＝ researchCapRedAudit Z1～Z10 ＋ T1～T3）", "減資名單筆數（原分類用）": ocnt, "新標籤筆數": tcnt,
           "版面": {"old": "~/evtdata/stitch_950ad26e12_b53f5540a8/data（scan ＝ ~/capred_work/scan_stitch.pkl）",
                  "v2": f"{ST_V2}（早年 reduce_v2；scan ＝ {CRW}/scan_stitch_v2.pkl）"},
           "reduce_ext_sha": E.REDUCE_EXT_SHA}
    # 沒解釋的跳動：期 × 分類（old vs v2）
    rows = []
    for w, R in S.items():
        U = R[R["type"] == "unexplained"]
        for (per, cl), g in U.groupby(["period", "cls"]):
            rows.append({"版面": w, "期": per, "分類": cl, "筆": len(g), "檔": g["sid"].nunique(), "上跳": int((g["adj_ratio"] > 1).sum()),
                         "價格規則沒擋": int((~g["px_bad"]).sum()), "價格規則沒擋且上跳": int(((~g["px_bad"]) & (g["adj_ratio"] > 1)).sum()),
                         "T1未解釋22": int(g["tag"].str.contains("資料庫未解釋22筆").sum()), "T2上市偵測176": int(g["tag"].str.contains("上市偵測176").sum()),
                         "T3上櫃偵測148": int(g["tag"].str.contains("上櫃偵測148").sum())})
    Q3 = pd.DataFrame(rows); Q3.to_csv(os.path.join(OUT, "unexplained_summary_old_vs_v2.csv"), index=False)
    piv = Q3.pivot_table(index=["期", "分類"], columns="版面", values="筆", fill_value=0).reset_index()
    SUM["沒解釋跳動｜期×分類（筆）"] = piv.to_dict("records")
    U2 = S["v2"][(S["v2"]["type"] == "unexplained") & (S["v2"]["period"] == "2004-2014")]
    U2[["sid", "mk", "cls", "tag", "p_date", "t_date", "gap", "raw_ratio", "adj_ratio", "shares_ratio", "px_bad", "eng_bad", "bp_rule"]].to_csv(
        os.path.join(OUT, "unexplained_early_v2.csv"), index=False, float_format="%.6g")
    # adj 減資事件（v2 早年）：連續與否、依 kind
    A = S["v2"][(S["v2"]["type"] == "reduce") & (S["v2"]["period"] == "2004-2014")].copy()
    A["kind2"] = np.where(A["red_kind"].str.startswith("上市偵測減資"), A["red_kind"], np.where(A["red_kind"] == "上櫃早年偵測減資", "上櫃早年偵測減資", "官方（TWTAUU／otcreduce）"))
    SUM["v2 早年 adj 減資事件（落在有效 K 棒）"] = {k: {"筆": int(len(g)), "還原後連續": int(g["continuous"].sum()), "不連續": int((~g["continuous"]).sum()),
                                                "不連續且價格規則壞根": int(((~g["continuous"]) & g["px_bad"]).sum())} for k, g in A.groupby("kind2")}
    A[["sid", "mk", "kind2", "red_date", "red_factor", "p_date", "t_date", "gap", "raw_ratio", "adj_ratio", "continuous", "phantom", "px_bad", "eng_bad"]].to_csv(
        os.path.join(OUT, "reduce_events_early_v2.csv"), index=False, float_format="%.6g")
    # s5 假飆股（old 重現＋v2）
    calS = {}
    for w, st in (("old", H("~/evtdata/stitch_950ad26e12_b53f5540a8/data")), ("v2", ST_V2)):
        D.DATA = st; calS[w] = D.load_calendar()
    assert (calS["old"] == calS["v2"]).all()
    s5r = {}; AG = {}
    for w, work in (("old", WORK5_OLD), ("v2", WORK5_V2)):
        R = S[w]; J = R[(R["type"] == "unexplained") & (~R["px_bad"]) & (R["adj_ratio"] > 1)]
        s5r[w], AG[w], _ = s5_cross(work, J, calS[w], CR)
    SUM["s5飆股網格｜假飆股"] = s5r
    orig = json.load(open("backtest/resultsCapRedAudit/summary.json", encoding="utf-8"))["s5飆股網格"]
    SUM["s5｜old 重現 ＝ 原 summary.json"] = all(orig[p][k] == s5r["old"][p][k] for p in ("2004-2014", "2015-") for k in orig[p])
    a = AG["v2"]; a = a[(a["per"] == "2004-2014") & a["fake"]].copy()
    a["類"] = np.where(a["tag"].str.contains("資料庫未解釋22筆"), "資料庫未解釋22筆", a["cls"])
    comp = a.groupby("類").agg(列=("M", "size"), 檔=("sid", "nunique")).reset_index()
    comp["不重複(s,d)"] = [int(a[a["類"] == k].drop_duplicates(["sid", "d"]).shape[0]) for k in comp["類"]]
    comp = comp.sort_values("列", ascending=False); comp.to_csv(os.path.join(OUT, "s5_fake_early_v2_by_class.csv"), index=False)
    SUM["v2 早年假飆股組成（列；跳動分類以 + 連接，未解釋22筆優先）"] = comp.to_dict("records")
    a2 = AG["v2"][AG["v2"]["per"] == "2004-2014"]
    top = a2[a2["fake"]].groupby("sid").size().sort_values(ascending=False).head(15)
    SUM["v2 早年假飆股｜列數前 15 檔"] = {k: int(v) for k, v in top.items()}
    for w in AG:
        AG[w].reset_index().groupby(["per", "strong", "red", "fake"]).size().rename("列").reset_index().to_csv(os.path.join(OUT, f"s5_cross_summary_{w}.csv"), index=False)
    # 網格（早年）old vs v2
    Go, mo = grid_early(WORK5_OLD); Gv, mv = grid_early(WORK5_V2)
    gold = pd.read_csv("backtest/resultsSurge5/grid.csv"); gold = gold[gold["段"] == "早年"].reset_index(drop=True)
    rep = bool((gold["事件"].to_numpy() == Go["事件"].to_numpy()).all() and (gold["定義域股日"].to_numpy() == Go["定義域股日"].to_numpy()).all()
               and np.allclose(gold["最大漲幅中位（H內）"].to_numpy(float), Go["最大漲幅中位（H內）"].to_numpy(float), rtol=2e-5, equal_nan=True))
    C = Go[["格", "H", "g"]].copy()
    for k in ("事件", "定義域股日", "比例", "最大漲幅中位（H內）", "最大漲幅中位（不設H，到回落30%前）"):
        C[f"{k}_old"] = Go[k]; C[f"{k}_v2"] = Gv[k]
    C["事件差"] = C["事件_v2"] - C["事件_old"]; C["中位差（H內）"] = C["最大漲幅中位（H內）_v2"] - C["最大漲幅中位（H內）_old"]
    C.to_csv(os.path.join(OUT, "grid_early_old_vs_v2.csv"), index=False, float_format="%.6g")
    rel = (C["事件_v2"] / C["事件_old"] - 1).replace([np.inf, -np.inf], np.nan)
    SUM["s5 早年網格（old vs v2）"] = {
        "old 重現 ＝ resultsSurge5/grid.csv 早年": rep, "old": mo, "v2": mv,
        "250 格事件合計": [int(C["事件_old"].sum()), int(C["事件_v2"].sum())],
        "事件數變動格數": int((C["事件差"] != 0).sum()), "事件數減少格數": int((C["事件差"] < 0).sum()), "事件數增加格數": int((C["事件差"] > 0).sum()),
        "各格事件相對變動｜中位、最小、最大": [float(np.nanmedian(rel)), float(np.nanmin(rel)), float(np.nanmax(rel))],
        "各格最大漲幅中位（H內）差｜中位、最小、最大（點）": [float(np.nanmedian(C["中位差（H內）"]) * 100), float(np.nanmin(C["中位差（H內）"]) * 100), float(np.nanmax(C["中位差（H內）"]) * 100)],
        "中位數變動格數（|差|>1e-6）": int((C["中位差（H內）"].abs() > 1e-6).sum()),
        "代表格": C[C["格"].isin(["H20_g50%", "H60_g100%", "H120_g100%", "H250_g100%", "H250_g200%", "H250_g500%"])][
            ["格", "事件_old", "事件_v2", "比例_old", "比例_v2", "最大漲幅中位（H內）_old", "最大漲幅中位（H內）_v2"]].to_dict("records")}
    json.dump(SUM, open(os.path.join(OUT, "summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    print(json.dumps({k: v for k, v in SUM.items() if k not in ("沒解釋跳動｜期×分類（筆）",)}, ensure_ascii=False, indent=1, default=str))
    print(piv.to_string())


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["gate", "early", "s5build", "scan", "report"])
    ap.add_argument("--procs", type=int, default=3)
    a = ap.parse_args()
    {"gate": gate, "early": early, "s5build": lambda: s5build(a.procs), "scan": lambda: scan(a.procs), "report": report}[a.mode]()

# -*- coding: utf-8 -*-
"""p9_panel_ext（面板補 2026-04～08 量測日，裁定線 seq167 §四）的 fixture。回測線，2026-09-25。

    cd ~/tw-p17 && PYTHONPATH=$HOME/tw-p17 ~/tw-p16/.venv/bin/python backtest/selftest_p9_panel_ext.py

⛔⛔ 本檔【不跑 P9 的 12 格】、⛔ 不讀也不存任何報酬：
   ・新增量測日的 fwd_* 由 p9_panel_ext 在寫檔前蓋成 NaN（E2）；本檔只驗「確實是 NaN」
   ・舊量測日那一段的 fwd_* 只參與「逐位元相同」的布林比對（它們本來就在 git 裡的 resultsAFC/panel.csv.gz），⛔ 不印不存值
   ・S5 呼叫引擎只為了拿種子 0 的【部位清單】（audit 的 side／t／sid），回傳的年化／回落等鍵當場丟掉、未讀未存
⭐ 預期值用獨立的算法（三分位用 selftest_p9_builders.expect_top 的整數名次規則；量測日用逐月 groupby 取首日），⛔ 不呼叫被測函式產預期。

  S1 重疊處：panel_ext 的 2026-03-02 以前 ＝ resultsAFC/panel.csv.gz【逐列逐欄逐位元】（值＋dtype），且解壓後的文字逐行相同；
     另證明比對分得出來（改一個位元 ⇒ 判不同）
  S2 新增量測日：日期 ＝ 獨立算的每月首個交易日；各日列數／eligible 檔數合理（對照舊面板最後 12 個量測日）；fwd_* 全 NaN；
     新列的股票 ⊆ gate3；(measure_date, stock_id) 不重複
  S3 無前視：2026-08-24 以後的價量／法人／股數／營收亂改（V1）⇒ 延伸出的量測日各欄【逐位元】不變；
     再加未來除權息因子（V2）⇒ ⚠ 不是逐位元（data.load_stock 的還原價＝原始價 × 含未來事件的累積因子，舊面板同樣如此，
     ⛔ 不是本件造成的）⇒ 驗 非浮點欄逐位元、連續欄 ≤ 1e-6、布林只在平手格翻、換進全體後前三分位不變；
     先證明「只算抽樣的幾檔 ＝ gate3 全體面板那幾檔」（面板欄全是逐檔量）、亂改真的被讀到；
     鑑別力：把亂改的起點提前到 2026-06-30 ⇒ 07-01、08-03 的列要變、04-01～06-01 不變
  S4 旗標：p9_flags 在延伸面板上 ⇒ 2026-03-02 以前的三分位與旗標與舊面板逐位元相同；2026-04～08 每個量測日都有旗標，
     且 ＝ 獨立整數規則；報每個量測日的 eligible／可排名／前三分位檔數
  S5 種子 0（default_rng(99000)、基準臂、門檻B 訊號取自舊面板＝P9 原樣）：持有期跨 2026-04～08 量測日的部位數（⛔ 只計數）
結果寫 backtest/resultsp9_engine/panel_ext_fixtures.json（新增檔）。
"""
from __future__ import annotations

import gzip
import json
import os
import shutil
import sys
import tempfile
import time

sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
import researchH2 as H2                       # noqa: E402  D.DATA ⇒ 快照、chdir ~/tw-p17
import numpy as np                            # noqa: E402
import pandas as pd                           # noqa: E402
import p9_panel_ext as X                      # noqa: E402  被測（建面板的程式）
import gate_b_status as GB                    # noqa: E402  panel_rows（＝ researchp4.panel_worker 逐檔呼叫）
import selftest_gate_b_status as SGB          # noqa: E402  _perturb（asof 之後亂改的既有實作）
from backtest import data as D                # noqa: E402
from backtest import p4_features as P         # noqa: E402
from backtest import p9_flags as F            # noqa: E402
from backtest import selftest_p9_builders as SB   # noqa: E402  expect_top（獨立整數規則）、setup_real、SEED0

OUT_JSON = os.path.join(X.OUT_DIR, "panel_ext_fixtures.json")
SEED = 20260925
N_SAMPLE_EL, N_SAMPLE_OTHER = 28, 12
RES: list = []
INFO: dict = {}


def chk(name, cond, detail=""):
    RES.append({"name": name, "ok": bool(cond), "detail": detail})
    print(("  ✓ " if cond else "  ✗ ") + name + (f"｜{detail}" if detail else ""), flush=True)
    return bool(cond)


def rt(df: pd.DataFrame) -> pd.DataFrame:
    """寫成 CSV 再用 read_panel 同一組參數讀回 ⇒ 比的是「檔案上的值」。"""
    import io
    b = io.StringIO(); df.to_csv(b, index=False); b.seek(0)
    return pd.read_csv(b, dtype={"stock_id": str}, parse_dates=["measure_date"], float_precision="round_trip")


def first_trading_day_each_month(cal: pd.DatetimeIndex, lo: str, hi: str) -> list[str]:
    """獨立算法：逐月 groupby 取最小日期（⛔ 不呼叫 measurement_days）。"""
    s = pd.Series(cal, index=cal)
    f = s.groupby([cal.year, cal.month]).min()
    return [str(d.date()) for d in f if pd.Timestamp(lo) <= d <= pd.Timestamp(hi)]


# ─────────────────────────────── S1
def s1(ext, old):
    print("── S1 重疊處逐位元")
    ov = ext[ext["measure_date"] <= pd.Timestamp(X.OLD_END)].reset_index(drop=True)
    ok, bad = X.frames_identical(ov, old)
    chk("S1a 欄名、欄序與 resultsAFC 完全相同", list(ext.columns) == list(old.columns), f"{len(ext.columns)} 欄")
    chk("S1b 2026-03-02 以前：逐列逐欄逐位元相同（值＋dtype；NaN 對 NaN）", ok,
        f"{len(ov):,} 列 vs {len(old):,} 列；不同欄 {bad}")
    a = gzip.open(X.OLD_PANEL, "rb").read().split(b"\n")
    b = gzip.open(X.OUT, "rb").read().split(b"\n")
    na = len(a) - (1 if a[-1] == b"" else 0)
    chk("S1c 解壓後文字：舊檔每一行（含表頭）＝ panel_ext 前面同樣行數逐位元組相同", a[:na] == b[:na], f"{na:,} 行")
    # 鑑別力：改一個位元 ⇒ 要判不同
    mut = old.copy()
    i = int(np.flatnonzero(mut["dist_hi120"].notna().to_numpy())[1000])
    v = np.array([mut.at[i, "dist_hi120"]], np.float64).view(np.int64); v ^= 1
    mut.at[i, "dist_hi120"] = v.view(np.float64)[0]
    ok2, bad2 = X.frames_identical(mut, old)
    mut2 = old.copy(); mut2.at[5, "eligible"] = not bool(mut2.at[5, "eligible"])
    ok3, _ = X.frames_identical(mut2, old)
    chk("S1d 比對分得出來：dist_hi120 改最低一個位元 ⇒ 判不同；eligible 翻一列 ⇒ 判不同", (not ok2) and (not ok3), f"{bad2}")
    INFO["overlap_rows"] = len(ov)


# ─────────────────────────────── S2
def s2(ext, old, cal, U):
    print("── S2 新增量測日")
    new = ext[ext["measure_date"] > pd.Timestamp(X.OLD_END)]
    got = sorted(str(d.date()) for d in new["measure_date"].unique())
    exp = first_trading_day_each_month(cal, "2026-04-01", X.ASOF)
    chk("S2a 新增量測日 ＝ 獨立算的 (2026-03-31, 2026-08-24] 每月首個交易日", got == exp, f"{got}")
    chk("S2b 沒有 2026-08-24 以後的量測日", new["measure_date"].max() <= pd.Timestamp(X.ASOF), str(new["measure_date"].max().date()))
    chk("S2c ⛔ 新增量測日的 fwd_20／60／120 全是 NaN（不存報酬）", bool(new[X.FWD].isna().all().all()), f"{len(new):,} 列 × 3 欄")
    chk("S2d (measure_date, stock_id) 不重複", not ext.duplicated(["measure_date", "stock_id"]).any())
    chk("S2e 新列的股票 ⊆ gate3", set(new["stock_id"]) <= set(U["stock_id"]), f"{new['stock_id'].nunique()} 檔")
    per = []
    for d, g in ext.groupby("measure_date"):
        per.append({"md": str(d.date()), "rows": len(g), "eligible": int(g["eligible"].astype(bool).sum())})
    per = pd.DataFrame(per)
    ref = per[per["md"] <= "2026-03-31"].tail(12)
    lo_r, hi_r = ref["rows"].min(), ref["rows"].max(); lo_e, hi_e = ref["eligible"].min(), ref["eligible"].max()
    pn = per[per["md"] > "2026-03-31"]
    ok_r = ((pn["rows"] >= 0.95 * lo_r) & (pn["rows"] <= 1.05 * hi_r)).all()
    ok_e = ((pn["eligible"] >= 0.75 * lo_e) & (pn["eligible"] <= 1.25 * hi_e)).all()
    chk("S2f 各新量測日列數落在舊面板最後 12 個量測日 [min×0.95, max×1.05]", bool(ok_r),
        f"舊 {lo_r}～{hi_r}；新 " + "、".join(f"{r.md}:{r.rows}" for r in pn.itertuples()))
    chk("S2g 各新量測日 eligible 檔數落在舊面板最後 12 個量測日 [min×0.75, max×1.25]", bool(ok_e),
        f"舊 {lo_e}～{hi_e}；新 " + "、".join(f"{r.md}:{r.eligible}" for r in pn.itertuples()))
    INFO["per_md_last12_old"] = ref.to_dict("records")
    INFO["per_md_new"] = pn.to_dict("records")


# ─────────────────────────────── S3
def _rows(sids, cal, newp, U):
    r = GB.panel_rows(sids, cal, newp, U)
    return rt(X.mask_fwd(r).reindex(columns=COLS))


def s3(ext, cal, U):
    print("── S3 無前視（2026-08-24 以後亂改）")
    _, newp = X.positions(cal)
    new = ext[ext["measure_date"] > pd.Timestamp(X.OLD_END)]
    rng = np.random.default_rng(SEED)
    el_s = sorted(set(new.loc[new["eligible"].astype(bool), "stock_id"]))
    ot_s = sorted(set(new["stock_id"]) - set(new.loc[new["eligible"].astype(bool), "stock_id"]))
    sids = sorted(set(rng.choice(el_s, N_SAMPLE_EL, replace=False)) | set(rng.choice(ot_s, N_SAMPLE_OTHER, replace=False)))
    mk = U.set_index("stock_id")["market"]
    INFO["s3_sample"] = {"n": len(sids), "twse": int((mk[sids] == "twse").sum()), "tpex": int((mk[sids] == "tpex").sum()), "sids": sids}
    ref = new[new["stock_id"].isin(set(sids))].sort_values(["measure_date", "stock_id"]).reset_index(drop=True)
    r0 = _rows(sids, cal, newp, U)
    ok, bad = X.frames_identical(r0, ref)
    chk("S3a 只算抽樣的幾檔（researchp4.panel_worker 逐檔）＝ gate3 全體 panel_ext 的那幾檔（⇒ 面板欄全是逐檔量）", ok,
        f"{len(sids)} 檔（twse {INFO['s3_sample']['twse']}、tpex {INFO['s3_sample']['tpex']}）、{len(ref)} 列；不同欄 {bad}")
    asof_pos = int(cal.searchsorted(pd.Timestamp(X.ASOF), side="right")) - 1
    src = D.DATA
    for adj_mode, tag in ((False, "V1 價量／法人／股數／營收"), (True, "V2 ＋未來除權息因子")):
        dst = tempfile.mkdtemp(prefix="p9ext_la_")
        try:
            SGB._perturb(src, os.path.join(dst, "data"), sids, asof_pos, cal, np.random.default_rng(SEED + adj_mode), adj_mode)
            live = 0
            for s in sids:
                D.DATA = src; a0 = P.stock_raw(s, mk[s], cal)["amt20"].to_numpy()[asof_pos + 1:]
                D.DATA = os.path.join(dst, "data"); a1 = P.stock_raw(s, mk[s], cal)["amt20"].to_numpy()[asof_pos + 1:]
                live += int(not np.array_equal(a0, a1, equal_nan=True))
            D.DATA = os.path.join(dst, "data")
            r1 = _rows(sids, cal, newp, U)
        finally:
            D.DATA = src
            shutil.rmtree(dst, ignore_errors=True)
        chk(f"S3b {tag}：亂改真的被讀到（2026-08-24 以後的 amt20 變了）", live >= len(sids) - 2, f"{live}/{len(sids)} 檔")
        ok, bad = X.frames_identical(r1, r0)
        if ok or not adj_mode:
            chk(f"S3c {tag}：新增量測日各欄逐位元不變", ok, f"{len(r0)} 列 × {len(r0.columns)} 欄；不同欄 {bad}")
        else:
            # 還原價 ＝ 原始價 × 含未來事件的累積因子（data.load_stock）⇒ 未來除權息讓過去的還原價【同乘一個常數】
            # ⇒ 比值型特徵數學上不變、浮點末位會動；布林欄（ma60_up、ma_stack）只可能在【原本就平手】的格翻。
            # ⭐ 這是 data.load_stock 還原法本身的性質（舊面板同樣如此），⛔ 不是本件延伸造成的；這裡把它量出來、並驗它只落在平手格。
            same_len = len(r1) == len(r0) and r1[["measure_date", "stock_id"]].equals(r0[["measure_date", "stock_id"]])
            flt = [c for c in r0.columns if r0[c].dtype.kind == "f"]
            cont = [c for c in flt if c not in ("ma60_up", "ma_stack")]
            nonf = [c for c in r0.columns if c not in flt]
            absd = max((float(np.nanmax(np.abs(r1[c].to_numpy() - r0[c].to_numpy()))) if r0[c].notna().any() else 0.0) for c in cont)
            same_nonf = same_len and all(r1[c].equals(r0[c]) for c in nonf) and all(np.array_equal(r1[c].isna(), r0[c].isna()) for c in flt)
            n_cells = int(sum((r1[c].to_numpy() != r0[c].to_numpy()).sum() - (r1[c].isna() & r0[c].isna()).sum() for c in flt))
            flips, gaps = [], []
            for c in ("ma60_up", "ma_stack"):
                for i in np.flatnonzero(~((r1[c] == r0[c]) | (r1[c].isna() & r0[c].isna())).to_numpy()):
                    s, d = r0.at[i, "stock_id"], r0.at[i, "measure_date"]; p_ = int(cal.get_loc(d))
                    cc = pd.Series(D.load_stock(s, mk[s], cal).df["close"].to_numpy()).ffill()
                    m20, m60, m120 = (cc.rolling(w, min_periods=w).mean().to_numpy() for w in (20, 60, 120))
                    if c == "ma60_up":
                        g = abs(m60[p_] - m60[p_ - 20]) / abs(m60[p_])
                    else:
                        g = min(abs(cc[p_] - m20[p_]) / abs(cc[p_]), abs(m20[p_] - m60[p_]) / abs(m20[p_]), abs(m60[p_] - m120[p_]) / abs(m60[p_]))
                    flips.append(f"{s}@{d.date()}:{c}"); gaps.append(float(g))
            # 決策層：把抽樣股的 V2 dist_hi120 換進 gate3 全體的延伸面板，重切 2026-04～08 的三分位 ⇒ 前三分位要完全相同
            newx = ext[ext["measure_date"] > pd.Timestamp(X.OLD_END)].reset_index(drop=True)
            key = pd.MultiIndex.from_frame(newx[["measure_date", "stock_id"]])
            sub = r1.set_index(["measure_date", "stock_id"])["dist_hi120"]
            hit = key.isin(sub.index)
            newv = newx.copy(); newv.loc[hit, "dist_hi120"] = sub.reindex(key[hit]).to_numpy()
            top0 = F.top_tercile(newx)["top"].to_numpy(); top1 = F.top_tercile(newv)["top"].to_numpy()
            n_top_flip = int((top0 != top1).sum())
            # ⚠ _perturb 的 V2 會把【所有列】的 cum_factor 以 %.8f 重寫 ⇒ 過去的還原價不只同乘常數、還帶 1e-8 級的捨入 ⇒ 容差取 1e-6
            ok_v2 = same_nonf and absd <= 1e-6 and all(g <= 1e-12 for g in gaps) and n_top_flip == 0
            chk(f"S3c {tag}：⚠ 不是逐位元不變（還原因子改寫 ⇒ 過去還原價同乘常數＋8 位小數捨入）；驗 非浮點欄與 NaN 位置逐位元不變、"
                f"連續欄絕對差 ≤ 1e-6、布林欄只在原值差 ≤ 1e-12 的平手格翻、換進全體後 2026-04～08 前三分位不變", ok_v2,
                f"末位不同 {n_cells} 格（欄 {bad}）；連續欄最大絕對差 {absd:.3g}；布林翻轉 {len(flips)} 格 {flips}（原值相對差 {[f'{g:.2g}' for g in gaps]}）；"
                f"換進 {int(hit.sum())} 列後前三分位翻轉 {n_top_flip}")
            INFO["s3_v2"] = {"cells_diff": n_cells, "cols": bad, "max_abs_diff_cont": absd, "flips": flips, "flip_gaps": gaps,
                             "top_flip_after_substitution": n_top_flip}
    # 鑑別力：亂改起點提前到 07-01 前一日 ⇒ 07-01、08-03 要變；04-01～06-01 不變
    cut = int(cal.searchsorted(pd.Timestamp("2026-07-01"))) - 1
    dst = tempfile.mkdtemp(prefix="p9ext_disc_")
    try:
        SGB._perturb(src, os.path.join(dst, "data"), sids, cut, cal, np.random.default_rng(SEED + 7), False)
        D.DATA = os.path.join(dst, "data")
        r2 = _rows(sids, cal, newp, U)
    finally:
        D.DATA = src
        shutil.rmtree(dst, ignore_errors=True)
    t7 = pd.Timestamp("2026-07-01")
    ok_e, _ = X.frames_identical(r2[r2["measure_date"] < t7].reset_index(drop=True), r0[r0["measure_date"] < t7].reset_index(drop=True))
    late0, late2 = r0[r0["measure_date"] >= t7], r2[r2["measure_date"] >= t7]
    m = late0.merge(late2, on=["measure_date", "stock_id"], how="inner", suffixes=("_0", "_2"))
    n_diff = int(sum((~((m[f"{c}_0"] == m[f"{c}_2"]) | (m[f"{c}_0"].isna() & m[f"{c}_2"].isna()))).sum() for c in ["amt20", "dist_hi120", "ret_20"]))
    chk("S3d 鑑別力：亂改起點提前到 2026-06-30 ⇒ 07-01／08-03 的列確實變了、04-01～06-01 逐位元不變（⇒ S3c 不是空轉）",
        ok_e and (n_diff > 0 or len(late0) != len(late2)),
        f"07-01／08-03 列數 {len(late0)}→{len(late2)}（亂改刪掉 15% 交易日 ⇒ 量測日無成交的列消失）；兩邊都在的 {len(m)} 列裡 amt20／dist_hi120／ret_20 變動格 {n_diff}")


# ─────────────────────────────── S4
def s4(ext, old, cal):
    print("── S4 2-B ⓑ 旗標")
    el_o = F.top_tercile(old).reset_index(drop=True)
    el_x = F.top_tercile(ext)
    el_xo = el_x[el_x["measure_date"] <= pd.Timestamp(X.OLD_END)].reset_index(drop=True)
    cols = ["measure_date", "stock_id", "dist", "ter", "top"]
    ok, bad = X.frames_identical(el_xo[cols], el_o[cols])
    chk("S4a 2026-03-02 以前：eligible 列、排名值、三分位桶、前三分位逐位元相同", ok, f"{len(el_o):,} 列；不同欄 {bad}")
    sids_o = sorted(set(old["stock_id"]))
    fo = F.build_flags(old, cal, sids=sids_o)
    fx = F.build_flags(ext, cal, sids=sids_o)
    cut = int(cal.searchsorted(pd.Timestamp(X.OLD_END), side="right"))
    same = all(np.array_equal(fo[s][:cut], fx[s][:cut]) for s in sids_o)
    old_after = sum(int(fo[s][cut:].sum()) for s in sids_o)
    chk("S4b build_flags：舊面板所有股票在 2026-03-31 以前的旗標序列逐位元相同", same, f"{len(sids_o):,} 檔")
    chk("S4c 舊面板在 2026-04 以後沒有任何旗標（＝ 補之前靜默當『不加碼』）", old_after == 0, f"{old_after}")
    rows = []; bad_n = 0; n_top_sum = 0
    fx_all = F.build_flags(ext, cal)
    for d, g in el_x[el_x["measure_date"] > pd.Timestamp(X.OLD_END)].groupby("measure_date", sort=True):
        exp = np.array(SB.expect_top(g["dist"].to_numpy()))
        bad_n += int((exp != g["top"].to_numpy()).sum())
        n_fin = int(np.isfinite(g["dist"].to_numpy()).sum())
        pos = int(cal.get_loc(d))
        n_flag = sum(int(f[pos]) for f in fx_all.values())
        rows.append({"md": str(d.date()), "eligible": len(g), "rankable": n_fin, "top_tercile": int(g["top"].sum()),
                     "expected_top_n_minus_floor_2n_3": n_fin - (2 * n_fin) // 3, "flags_true": n_flag})
        n_top_sum += int(g["top"].sum())
    ok_cnt = all(r["top_tercile"] == r["expected_top_n_minus_floor_2n_3"] == r["flags_true"] and r["top_tercile"] > 0 for r in rows)
    chk("S4d 2026-04～08 每個量測日：前三分位 ＝ 獨立整數規則（逐列）", bad_n == 0 and len(rows) == 5, f"{len(rows)} 個量測日、不符 {bad_n}")
    chk("S4e 每個新量測日都有旗標，且 前三分位檔數 ＝ n − ⌊2n/3⌋ ＝ build_flags 在該日為真的檔數", ok_cnt,
        "；".join(f"{r['md']}：eligible {r['eligible']}／可排名 {r['rankable']}／前三分位 {r['top_tercile']}" for r in rows))
    non_md = sum(int(f[cut:].sum()) for f in fx_all.values()) - n_top_sum
    chk("S4f 2026-04 以後旗標只出現在量測日", non_md == 0, f"量測日以外為真 {non_md}")
    INFO["flags_new_md"] = rows
    return fx_all


# ─────────────────────────────── S5
def s5(ext, fx_all):
    print("── S5 種子 0 部位（⛔ 只計數）")
    from backtest import research11 as R
    SB.setup_real(log=lambda s: None)
    G = SB._G
    cal, sig, ncal = G["cal"], G["sig"], G["ncal"]
    au = []
    o = R.simulate_mtm(sig, SB.RULE, SB.N_MAIN, np.random.default_rng(SB.SEED0), G["closes"], G["opens"], ncal, audit=au)
    del o                                                        # ⛔ 年化／回落等鍵不讀、不存
    buys = [(a["sid"], int(a["t"])) for a in au if a["side"] == "buy"]
    del au
    exit_of = dict(zip(zip(sig["sid"], sig["entry_pos"]), sig[f"xpos_{SB.RULE}"]))
    _, newp = X.positions(cal)
    oldp = X.positions(cal)[0]; oldp = oldp[cal[oldp] <= pd.Timestamp(X.OLD_END)]
    elig = {(pd.Timestamp(d), s) for d, s in zip(ext.loc[ext["eligible"].astype(bool), "measure_date"], ext.loc[ext["eligible"].astype(bool), "stock_id"])}
    n_pos = n_pos_loose = 0; per = {str(cal[m].date()): {"held_readable": 0, "eligible": 0, "top": 0} for m in newp}
    n_after_old = 0
    for sid, e in buys:
        x = int(exit_of[(sid, e)])
        hit = [m for m in newp if e <= m <= x - 2]               # 引擎在 m+1 ≤ x−1 開盤讀得到（同 selftest_p9_builders R4c）
        n_pos += int(bool(hit))
        n_pos_loose += int(any(e <= m <= x for m in newp))
        n_after_old += int(x - 2 > int(oldp.max()))
        for m in hit:
            k = str(cal[m].date()); per[k]["held_readable"] += 1
            per[k]["eligible"] += int((cal[m], sid) in elig); per[k]["top"] += int(fx_all.get(sid, np.zeros(ncal, bool))[m])
    rd = {"部位數（種子 0 基準臂）": len(buys), "持有期跨 2026-04～08 量測日的部位（e ≤ m ≤ x−2，引擎讀得到）": n_pos,
          "同上，寬口徑（e ≤ m ≤ x）": n_pos_loose, "對照：持有期超過舊面板最後量測日的部位（R4c 口徑，應 ＝ 8）": n_after_old,
          "逐量測日": per}
    chk("S5 種子 0：持有期跨 2026-04～08 量測日的部位數（只計數）", n_after_old == 8 and n_pos <= n_after_old,
        json.dumps(rd, ensure_ascii=False))
    INFO["seed0"] = rd


COLS: list = []


def main():
    t0 = time.time()
    cal = D.load_calendar()
    chk("S0 資料＝main 快照 edc6f8002f", H2.SHA.startswith("edc6f8002f") and D.DATA == H2.H2D, f"D.DATA＝{D.DATA}；日曆 {len(cal)} 根～{cal[-1].date()}")
    U = X.load_gate3()
    old = P.read_panel(X.OLD_PANEL)
    ext = P.read_panel(X.OUT)
    COLS.extend(old.columns)
    s1(ext, old)
    s2(ext, old, cal, U)
    s3(ext, cal, U)
    fx_all = s4(ext, old, cal)
    s5(ext, fx_all)
    fail = sum(not r["ok"] for r in RES)
    d = {"when": pd.Timestamp.now(tz="Asia/Taipei").strftime("%Y-%m-%d %H:%M"), "n": len(RES), "fail": fail,
         "secs": round(time.time() - t0), "checks": RES, "info": INFO}
    json.dump(d, open(OUT_JSON, "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    print(f"\n{'✅ 全部通過' if not fail else f'⛔ {fail} 條沒過'}：{len(RES)} 條（{time.time() - t0:.0f}s）⇒ {OUT_JSON}")
    sys.exit(1 if fail else 0)


if __name__ == "__main__":
    main()

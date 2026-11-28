# -*- coding: utf-8 -*-
"""scanadd：S83 漲停次數（官方漲跌停價；裁定 seq520、seq526 §3、seq532 §二）——只算因子值，⛔ 不算任何報酬。
官方價：tw-stock-data data/universe/pricelimit（上市）、otcpricelimit（上櫃），git archive 抽到 ~/s83_limits_data（SHA.txt 記 commit）。
⛔⛔ 兩支日期意義相反（docs/READ_CONTRACT.md 文末一節）：
  上市 pricelimit/<d>.csv 的 limit_up ＝ d 當天的漲停價；
  上櫃 otcpricelimit/<d>.csv 的 next_limit_up ＝ d 的下一交易日的漲停價 ⇒ 要 d 日的價，讀 <d 的前一交易日>.csv。
每個股票日（面板有效根）：
  市場＝該股日線 stocks/<sid>.csv 當天的 market 欄（twse → 上市檔；tpex → 上櫃檔）；
  漲停價 9999.95 或跌停價 0.01（沒有漲跌幅限制）⇒ 排除，記缺值（seq532）；
  查不到漲停價 ⇒ 不判，記缺值（恢復交易首日＝前一交易日沒有有效根，另計數）；⛔ 不推算漲停價；
  d 日漲停 ＝ d 日收盤（未還原）≥ d 日官方漲停價（容差 1e-6）。
S83＝形成月最後交易日往回 20 根內漲停天數（同 64 格 S83alt／S11 寫法：factors.roll(·, 20, "sum", 15)，有值根 ≥15）；方向取高（0134 第 4 點：沒寫方向一律取高）。
輸出：~/scanadd/factors/S83.parquet；~/scanadd/s83/upoff.npz（逐日 0／1／缺值與缺值原因）、s83_coverage.csv。"""
import os, sys
import numpy as np, pandas as pd

NOLIM_UP, NOLIM_DN, TOL = 9999.0, 0.011, 1e-6
# 狀態碼
ST_INVALID, ST_OK, ST_NOLIMIT, ST_MISS_RESUME, ST_MISS_OTHER, ST_NOMARKET = 0, 1, 2, 3, 4, 5


def read_limits(limdir, cal, sids):
    """回傳 (TW_UP, TW_DN, OTC_UP, OTC_DN)：T×N，皆已對齊成「該日適用」的價（上櫃已往後移一個交易日）。"""
    T, N = len(cal), len(sids); col = {s: j for j, s in enumerate(sids)}
    out = {k: np.full((T, N), np.nan) for k in ("TU", "TD", "OU", "OD")}
    ds = cal.strftime("%Y-%m-%d")
    pl = os.path.join(limdir, "pricelimit"); ol = os.path.join(limdir, "otcpricelimit")
    for t, d in enumerate(ds):
        p = os.path.join(pl, f"{d}.csv")
        if os.path.exists(p):
            x = pd.read_csv(p, dtype=str)
            assert (x["date"] == d).all(), p
            j = x["stock_id"].map(col); m = j.notna().to_numpy(); jj = j[m].astype(int).to_numpy()
            out["TU"][t, jj] = pd.to_numeric(x.loc[m, "limit_up"]).to_numpy()
            out["TD"][t, jj] = pd.to_numeric(x.loc[m, "limit_down"]).to_numpy()
        p = os.path.join(ol, f"{d}.csv")
        if os.path.exists(p) and t + 1 < T:              # <d>.csv 的 next_* ＝ cal[t+1] 適用
            x = pd.read_csv(p, dtype=str)
            assert (x["date"] == d).all(), p
            j = x["stock_id"].map(col); m = j.notna().to_numpy(); jj = j[m].astype(int).to_numpy()
            out["OU"][t + 1, jj] = pd.to_numeric(x.loc[m, "next_limit_up"]).to_numpy()
            out["OD"][t + 1, jj] = pd.to_numeric(x.loc[m, "next_limit_down"]).to_numpy()
    return out["TU"], out["TD"], out["OU"], out["OD"]


def classify(RC, VALID, MKT, TU, TD, OU, OD):
    """RC：未還原收盤；VALID：有效根；MKT：'twse'／'tpex'／''。回傳 (UPOFF 0/1/NaN, ST 狀態碼, LU 採用的漲停價)。"""
    tw = MKT == "twse"; ot = MKT == "tpex"
    LU = np.where(tw, TU, np.where(ot, OU, np.nan)); LD = np.where(tw, TD, np.where(ot, OD, np.nan))
    ST = np.full(RC.shape, ST_INVALID, np.int8)
    v = VALID & np.isfinite(RC)
    prev_valid = np.vstack([np.zeros((1, RC.shape[1]), bool), v[:-1]])
    nolim = (LU >= NOLIM_UP) | (LD <= NOLIM_DN)
    has = np.isfinite(LU)
    ST[v & ~(tw | ot)] = ST_NOMARKET
    ST[v & (tw | ot) & ~has & ~prev_valid] = ST_MISS_RESUME
    ST[v & (tw | ot) & ~has & prev_valid] = ST_MISS_OTHER
    ST[v & (tw | ot) & has & nolim] = ST_NOLIMIT
    ok = v & (tw | ot) & has & ~nolim
    ST[ok] = ST_OK
    UP = np.full(RC.shape, np.nan)
    UP[ok] = (RC[ok] >= LU[ok] - TOL).astype(float)
    return UP, ST, LU


def load_market(stocks_dir, cal, sids):
    """市場別與未還原收盤（float64，直接由日線字串轉；⚠ 不用面板 float32 的 RC：千元價位 float32 誤差可達 3e-5，會讓「收盤＝漲停價」判錯）。"""
    MKT = np.full((len(cal), len(sids)), "", dtype=object); RC = np.full((len(cal), len(sids)), np.nan)
    for j, s in enumerate(sids):
        p = os.path.join(stocks_dir, f"{s}.csv")
        if not os.path.exists(p):
            continue
        x = pd.read_csv(p, dtype=str, usecols=["date", "market", "close"]).drop_duplicates("date")
        x["date"] = pd.to_datetime(x["date"]); x = x.set_index("date").reindex(cal)
        MKT[:, j] = x["market"].fillna("").to_numpy()
        RC[:, j] = pd.to_numeric(x["close"], errors="coerce").to_numpy()
    return MKT.astype(str), RC


def main():
    import snap
    import factors as F             # 共用 factors.py 的 roll、save、面板（唯一實作）
    D = snap.fix(); snap.check()
    LIMROOT = os.path.expanduser(os.environ.get("S83_LIMITS", "~/s83_limits_data"))
    LIMSHA = open(os.path.join(LIMROOT, "SHA.txt")).read().strip()
    limdir = os.path.join(LIMROOT, "data", "universe")
    OUT = os.path.join(snap.BASE, "s83"); os.makedirs(OUT, exist_ok=True)
    cal, sids = F.cal, F.sids
    files = {k: sorted(f[:-4] for f in os.listdir(os.path.join(limdir, k))) for k in ("pricelimit", "otcpricelimit")}
    ds = list(cal.strftime("%Y-%m-%d"))
    for k, v in files.items():
        print(k, "檔數", len(v), "＝日曆" if v == ds else f"⚠ 與日曆不同：多 {sorted(set(v) - set(ds))[:5]} 少 {sorted(set(ds) - set(v))[:5]}")
    VALID = F.VALID
    MKT, RC = load_market(os.path.join(D.DATA, "stocks"), cal, sids)
    RC[~VALID] = np.nan
    d32 = np.nanmax(np.abs(RC - np.where(VALID, F.M["RC"], np.nan)) / RC)
    print("日線收盤 float64 vs 面板 RC float32 最大相對差", d32)
    assert d32 < 1e-6
    TU, TD, OU, OD = read_limits(limdir, cal, sids)
    UP, ST, LU = classify(RC, VALID, MKT, TU, TD, OU, OD)
    np.savez_compressed(os.path.join(OUT, "upoff.npz"), cal=np.array(ds), sids=np.array(sids), UP=UP.astype(np.float32), ST=ST, LU=LU.astype(np.float32))
    # 市場別不符（上市日卻只在上櫃檔、或反之）只計數
    v = VALID & np.isfinite(RC)
    mism_tw = int((v & (MKT == "twse") & ~np.isfinite(TU) & np.isfinite(OU)).sum())
    mism_ot = int((v & (MKT == "tpex") & ~np.isfinite(OU) & np.isfinite(TU)).sum())
    over_m = np.isfinite(UP) & (RC > LU + TOL)
    over = int(over_m.sum())
    t_, j_ = np.nonzero(over_m)      # 只列出；照「≥」規則照算漲停（⛔ 不改價、不推算）
    pd.DataFrame(dict(date=cal[t_].strftime("%Y-%m-%d"), stock_id=np.array(sids)[j_], market=MKT[t_, j_], close=RC[t_, j_], limit_up=LU[t_, j_])).to_csv(
        os.path.join(OUT, "s83_close_above_limit.csv"), index=False)
    # 涵蓋（全面板有效根，與母體內有效根；2015-01-05 起）
    U_df = pd.read_parquet(os.path.join(F.FAC, "universe.parquet")); U = U_df.to_numpy(bool)
    me = pd.DatetimeIndex(pd.to_datetime(U_df.index))
    kpos = me.searchsorted(cal, side="left") - 1          # 各日之前最近月底母體（只為涵蓋描述）
    inU = np.zeros_like(v)
    for t in range(len(cal)):
        if kpos[t] >= 0:
            inU[t] = U[kpos[t]]
    rows = []
    names = {ST_OK: "有官方價可判", ST_NOLIMIT: "沒有漲跌幅限制(9999.95/0.01)排除", ST_MISS_RESUME: "缺值_恢復交易首日查不到", ST_MISS_OTHER: "缺值_其他查不到", ST_NOMARKET: "日線無市場別"}
    for scope, m in (("全面板有效根", v), ("母體內有效根(前一月底母體)", v & inU)):
        for mk in ("twse", "tpex"):
            mm = m & (MKT == mk)
            r = {"範圍": scope, "市場": mk, "有效根": int(mm.sum())}
            for k, nm in names.items():
                r[nm] = int((mm & (ST == k)).sum())
            r["漲停根"] = int(np.nansum(np.where(mm, UP, np.nan)))
            r["漲停比例(可判根)"] = round(r["漲停根"] / max(r["有官方價可判"], 1), 5)
            rows.append(r)
    cov = pd.DataFrame(rows)
    cov["市場別不符(上市日只在上櫃檔/上櫃日只在上市檔)"] = f"{mism_tw}/{mism_ot}"
    cov["收盤>漲停價+1e-6"] = over
    cov["官方價來源"] = LIMSHA
    cov.to_csv(os.path.join(OUT, "s83_coverage.csv"), index=False, encoding="utf-8-sig")
    print(cov.drop(columns=["官方價來源"]).T.to_string())
    # 因子：同 64 格 S83alt（factors.py price_factors：up = np.where(VALID, UP, nan); roll(up, 20, "sum", 15)）
    up = np.where(VALID, UP, np.nan)
    F.save("S83", F.roll(up, 20, "sum", 15))
    print("官方價", LIMSHA, "｜價量母體", snap.SHA)
    snap.check()


if __name__ == "__main__":
    main()

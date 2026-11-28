# -*- coding: utf-8 -*-
"""S83 官方漲跌停價讀法 fixture（seq532 §二：上市、上櫃各驗一天）。⛔ 不算任何報酬。
一、合成 fixture：假造 4 個交易日的 pricelimit／otcpricelimit 檔，驗 s83_limit.read_limits／classify 的日期對齊、9999.95 排除、恢復交易首日缺值。
二、真資料手算對照：上市、上櫃各挑一個母體內漲停日，印出官方檔原始列與日線收盤，並印「讀錯檔」會拿到的值。
三、全期對齊驗算：上市 pricelimit/<d>.prev_close ＝ d 前一交易日收盤；上櫃 otcpricelimit/<d>.close ＝ d 收盤（證明 <d> 檔的 next_* 屬於 d 的下一交易日）。"""
import os, tempfile
import numpy as np, pandas as pd
import s83_limit as L


def synthetic():
    cal = pd.DatetimeIndex(["2024-07-01", "2024-07-02", "2024-07-03", "2024-07-04"])
    sids = ["1111", "2222", "3333", "4444"]       # 1111 上市；2222 上櫃；3333 上櫃、07-02 停牌、07-03 恢復；4444 上市、沒有漲跌幅限制
    d = tempfile.mkdtemp(prefix="s83fx_")
    os.makedirs(os.path.join(d, "pricelimit")); os.makedirs(os.path.join(d, "otcpricelimit"))
    tw = {  # 上市：<d> 檔＝d 當天
        "2024-07-01": [("1111", "11.00", "9.00"), ("4444", "9999.95", "0.01")],
        "2024-07-02": [("1111", "12.10", "9.90"), ("4444", "9999.95", "0.01")],
        "2024-07-03": [("1111", "13.30", "10.90"), ("4444", "9999.95", "0.01")],
        "2024-07-04": [("1111", "14.60", "12.00"), ("4444", "9999.95", "0.01")]}
    ot = {  # 上櫃：<d> 檔的 next_* ＝ d 的下一交易日
        "2024-07-01": [("2222", "20.00", "22.00", "18.00"), ("3333", "30.00", "33.00", "27.00")],
        "2024-07-02": [("2222", "22.00", "24.20", "19.80")],                 # 3333 停牌 ⇒ 沒有列 ⇒ 07-03 查不到
        "2024-07-03": [("2222", "21.00", "23.10", "18.90"), ("3333", "33.00", "36.30", "29.70")],
        "2024-07-04": [("2222", "23.10", "25.40", "20.80"), ("3333", "36.30", "39.90", "32.70")]}
    for k, rows in tw.items():
        pd.DataFrame([(k, s, u, dn, "", "", "", "") for s, u, dn in rows],
                     columns=["date", "stock_id", "limit_up", "limit_down", "open_base", "prev_close", "prev_open_base", "last_trade_date"]).to_csv(os.path.join(d, "pricelimit", f"{k}.csv"), index=False)
    for k, rows in ot.items():
        pd.DataFrame([(k, s, c, u, dn) for s, c, u, dn in rows], columns=["date", "stock_id", "close", "next_limit_up", "next_limit_down"]).to_csv(os.path.join(d, "otcpricelimit", f"{k}.csv"), index=False)
    RC = np.array([[10.0, 20.0, 30.0, 50.0],
                   [12.1, 22.0, np.nan, 60.0],    # 1111 07-02 收 12.10 ＝ 當天上市漲停價 ⇒ 漲停；2222 07-02 收 22.00 ＝ 07-01 檔 next 22.00 ⇒ 漲停
                   [12.5, 21.0, 33.0, 70.0],      # 3333 07-03 恢復交易：07-02 檔沒有列 ⇒ 缺值（即使收盤 33.00 ＝ 07-01 檔 next）
                   [14.6, 23.1, 36.3, 80.0]])     # 2222 07-04 收 23.10 ＝ 07-03 檔 next 23.10 ⇒ 漲停（若誤讀 07-04 檔 next 25.40 ⇒ 不漲停）
    VALID = np.isfinite(RC)
    MKT = np.array([["twse", "tpex", "tpex", "twse"]] * 4)
    TU, TD, OU, OD = L.read_limits(d, cal, sids)
    UP, ST, LU = L.classify(RC, VALID, MKT, TU, TD, OU, OD)
    exp_UP = np.array([[0, np.nan, np.nan, np.nan],      # 2222、3333 07-01：前一交易日檔不在範圍 ⇒ 缺值；4444 全部沒有漲跌幅限制 ⇒ 缺值
                       [1, 1, np.nan, np.nan],
                       [0, 0, np.nan, np.nan],
                       [1, 1, 1, np.nan]])
    assert np.array_equal(np.isnan(UP), np.isnan(exp_UP)) and np.array_equal(UP[~np.isnan(UP)], exp_UP[~np.isnan(exp_UP)]), UP
    assert ST[2, 2] == L.ST_MISS_RESUME and ST[1, 2] == L.ST_INVALID and (ST[:, 3] == L.ST_NOLIMIT).all()
    assert LU[3, 1] == 23.10 and LU[1, 0] == 12.10 and LU[3, 2] == 36.30
    print("一、合成 fixture 通過：上市讀 <d> 的 limit_up、上櫃讀 <d−1> 的 next_limit_up；9999.95 排除；恢復交易首日缺值。")


def real():
    import snap
    import factors as F
    D = snap.fix(); snap.check()
    root = os.path.join(os.path.expanduser(os.environ.get("S83_LIMITS", "~/s83_limits_data")), "data", "universe")
    Z = np.load(os.path.join(snap.BASE, "s83", "upoff.npz"))
    cal = pd.DatetimeIndex(Z["cal"]); sids = list(Z["sids"]); UP = Z["UP"]
    MKT, RC = L.load_market(os.path.join(D.DATA, "stocks"), cal, sids); RC[~F.VALID] = np.nan
    U_df = pd.read_parquet(os.path.join(F.FAC, "universe.parquet"))
    k = list(U_df.index).index("2024-06-28"); inU = U_df.iloc[k].to_numpy(bool)
    out = []
    for mk in ("twse", "tpex"):
        t = int(cal.get_loc(pd.Timestamp("2024-07-01")))
        while True:
            js = np.flatnonzero(inU & (MKT[t] == mk) & (UP[t] == 1))
            if len(js):
                break
            t += 1
        j = js[0]; d = cal[t].strftime("%Y-%m-%d"); dm1 = cal[t - 1].strftime("%Y-%m-%d"); s = sids[j]
        if mk == "twse":
            x = pd.read_csv(os.path.join(root, "pricelimit", f"{d}.csv"), dtype=str).set_index("stock_id").loc[s]
            print(f"二、上市 {s} {d}：pricelimit/{d}.csv → limit_up {x.limit_up}、prev_close {x.prev_close}；日線 {d} 收盤 {RC[t, j]:.2f}、{dm1} 收盤 {RC[t - 1, j]:.2f}"
                  f" ⇒ 收盤 {RC[t, j]:.2f} ≥ {x.limit_up} ⇒ 漲停；程式 UP＝{UP[t, j]:.0f}、LU＝{Z['LU'][t, j]:.2f}")
            assert abs(float(x.limit_up) - RC[t, j]) < 1e-6 and abs(float(x.prev_close) - RC[t - 1, j]) < 1e-6
        else:
            a = pd.read_csv(os.path.join(root, "otcpricelimit", f"{dm1}.csv"), dtype=str).set_index("stock_id").loc[s]
            b = pd.read_csv(os.path.join(root, "otcpricelimit", f"{d}.csv"), dtype=str).set_index("stock_id").loc[s]
            print(f"二、上櫃 {s} {d}：otcpricelimit/{dm1}.csv → close {a.close}（＝日線 {dm1} 收盤 {RC[t - 1, j]:.2f}）、next_limit_up {a.next_limit_up}；"
                  f"日線 {d} 收盤 {RC[t, j]:.2f} ⇒ 收盤 ≥ {a.next_limit_up} ⇒ 漲停；程式 UP＝{UP[t, j]:.0f}、LU＝{Z['LU'][t, j]:.2f}。"
                  f"⛔ 若誤讀 otcpricelimit/{d}.csv：close {b.close}、next_limit_up {b.next_limit_up}（那是 {cal[t + 1].date()} 的價）")
            assert abs(float(a.next_limit_up) - RC[t, j]) < 1e-6 and abs(float(a.close) - RC[t - 1, j]) < 1e-6 and float(b.next_limit_up) != float(a.next_limit_up)
        out.append((mk, s, d))
    # 三、全期對齊驗算
    col = {s: j for j, s in enumerate(sids)}
    n_tw = ok_tw = n_ot = ok_ot = 0
    for t, d in enumerate(cal.strftime("%Y-%m-%d")):
        x = pd.read_csv(os.path.join(root, "pricelimit", f"{d}.csv"), dtype=str)
        x = x[x.stock_id.isin(col) & (x.prev_close.fillna("") != "")]
        if t > 0 and len(x):
            jj = x.stock_id.map(col).to_numpy(); pc = pd.to_numeric(x.prev_close).to_numpy(); prev = RC[t - 1, jj]
            m = np.isfinite(prev) & (MKT[t - 1, jj] == "twse")
            n_tw += int(m.sum()); ok_tw += int((np.abs(pc[m] - prev[m]) < 1e-6).sum())
        y = pd.read_csv(os.path.join(root, "otcpricelimit", f"{d}.csv"), dtype=str)
        y = y[y.stock_id.isin(col)]
        jj = y.stock_id.map(col).to_numpy(); c = pd.to_numeric(y.close, errors="coerce").to_numpy(); cur = RC[t, jj]
        m = np.isfinite(cur) & np.isfinite(c) & (MKT[t, jj] == "tpex")
        n_ot += int(m.sum()); ok_ot += int((np.abs(c[m] - cur[m]) < 1e-6).sum())
    print(f"三、全期對齊：上市 prev_close＝前一交易日收盤 {ok_tw:,}／{n_tw:,}；上櫃 <d>.close＝d 收盤 {ok_ot:,}／{n_ot:,}")
    return out


if __name__ == "__main__":
    synthetic()
    real()

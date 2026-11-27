# -*- coding: utf-8 -*-
"""scanadd step 4：S29、S87 單因子描述掃描報酬（登錄 回測 1120-0053＋0054；讀法 1120-0134 第三節；裁定 seq520、seq526）。
做法與 backtest/resultsScan64/code/returns.py 的橫斷面部分逐行相同（月持有、前五分之一對母體、Q1−Q5、IC、換手扣 0.585%、
循環區塊自助法 6 個月 4,000 次 seed 5、假訊號＝每月母體內打亂因子值 default_rng(5)），只改：
  - 因子清單只有 S29、S87（S30 登錄歧義不跑）；
  - Bonferroni 依 seq526：同族 64＋新格數，新格數未定（4 或 5）⇒ 0.05/68 與 0.05/69 兩種都算、並列；
  - 另報自助法雙尾 p（百分位法 2×min 尾比例，只描述；判語照區間）。
用法：returns_add.py dry  ⇒ 報酬全寫 0（還原收盤一律換 1），輸出到 ~/scanadd/dry/；
      returns_add.py real ⇒ 正式跑，輸出到 ~/scanadd/。"""
import os, sys, time
import numpy as np, pandas as pd
import snap
from backtest import data as D
D = snap.fix()

MODE = sys.argv[1] if len(sys.argv) > 1 else "dry"
assert MODE in ("dry", "real", "fixture")
t0 = time.time()
BASE = snap.BASE
FAC = os.path.join(BASE, "factors"); CACHE = os.path.join(BASE, "cache")
OUT = BASE if MODE == "real" else os.path.join(BASE, MODE)
OUT_M = os.path.join(OUT, "monthly"); os.makedirs(OUT_M, exist_ok=True)

EXP = ("2017-03", "2021-12"); CON = ("2022-01", "2026-08")
MIN_VAL, MIN_TOP_BIN, MIN_GROUPS = 50, 5, 24
A95 = 0.05
NC = {"68": 68, "69": 69}
AB = {k: 0.05 / n for k, n in NC.items()}
B, BLOCK, SEED = 4000, 6, 5
COST = 0.00585
SPEC = [("S29", "籌碼", "內部人持股增加", "橫斷面", "high"),
        ("S87", "籌碼", "董監持股比例水準", "橫斷面", "high"),
        ("S30", "籌碼", "內部人質押比上升（seq527：董監質押比月變化）", "橫斷面", "high")]
ONLY = sys.argv[2:]            # 指定只跑哪幾格（seq527：S30 單獨補跑，S29、S87 不重跑）；結果併入既有 result_add.csv
if ONLY:
    SPEC = [s for s in SPEC if s[0] in ONLY]
    assert len(SPEC) == len(ONLY), ONLY


def seg_of(s):
    s = str(s)
    if EXP[0] <= s <= EXP[1]:
        return "探索"
    if CON[0] <= s <= CON[1]:
        return "確認"
    return None


P = np.load(os.path.join(CACHE, "panel.npz"))
cal = pd.DatetimeIndex(pd.to_datetime(P["cal"])); sids = [str(s) for s in P["sids"]]
VALID = P["VALID"] == 1
C = P["C"].astype(float); C[~VALID] = np.nan
if MODE == "dry":
    C = np.where(np.isfinite(C), 1.0, np.nan)          # ⛔ 乾跑：報酬全 0（保留有效／缺值樣態）
if MODE == "fixture":                                   # 合成 fixture：隨機漫步假價格（非真報酬），只為讓 IC 等欄有變異可驗
    _r = np.random.default_rng(123).normal(0, 0.02, C.shape)
    C = np.where(np.isfinite(C), np.exp(np.cumsum(_r, 0)), np.nan)
BAD = np.nan_to_num(P["BAD"]) > 0
T, N = C.shape
Cff = pd.DataFrame(C).ffill().to_numpy()
CB = np.vstack([np.zeros((1, N)), np.cumsum(BAD, 0)])
DATA_LAST = cal[np.flatnonzero(VALID.any(1))[-1]]

U_df = pd.read_parquet(os.path.join(FAC, "universe.parquet"))
me_dates = pd.DatetimeIndex(pd.to_datetime(U_df.index))
assert list(U_df.columns) == sids
U = U_df.to_numpy(bool)
me_pos = np.array([cal.get_loc(d) for d in me_dates])
NM = len(me_pos)
RM = np.full((NM, N), np.nan); hold_m = []
for i in range(NM):
    hold_m.append(str(me_dates[i].to_period("M") + 1))
    if i + 1 < NM:
        e = me_pos[i] + 1; x = me_pos[i + 1]
        RM[i] = Cff[x] / C[e] - 1
        RM[i][(CB[x + 1] - CB[e + 1]) > 0] = np.nan
hold_m = np.array(hold_m)
UM = np.array([np.nanmean(np.where(U[i] & np.isfinite(RM[i]), RM[i], np.nan)) if (U[i] & np.isfinite(RM[i])).any() else np.nan for i in range(NM)])
seg_m = np.array([seg_of(h) for h in hold_m])
if MODE == "dry":
    assert np.nanmax(np.abs(RM)) == 0, "乾跑報酬不是 0"

_IDX = {}


def cbb_idx(n):
    if n not in _IDX:
        rng = np.random.default_rng(SEED)
        nb = int(np.ceil(n / BLOCK))
        st = rng.integers(0, n, size=(B, nb))
        _IDX[n] = ((st[:, :, None] + np.arange(BLOCK)[None, None, :]) % n).reshape(B, -1)[:, :n]
    return _IDX[n]


def boot(x):
    x = np.asarray(x, float); x = x[np.isfinite(x)]; n = len(x)
    keys = ["mean", "lo95", "hi95", "loB68", "hiB68", "loB69", "hiB69", "p", "n"]
    if n < 2:
        return dict(zip(keys, [np.nanmean(x) if n else np.nan] + [np.nan] * 7 + [n]))
    m = x[cbb_idx(n)].mean(1)
    q = np.quantile(m, [A95 / 2, 1 - A95 / 2, AB["68"] / 2, 1 - AB["68"] / 2, AB["69"] / 2, 1 - AB["69"] / 2])
    p = min(1.0, 2 * min((m <= 0).mean(), (m >= 0).mean()))
    return dict(zip(keys, [x.mean(), *q, p, n]))


def cross_series(V, dirn):
    rows = []; prev_top = None; prev_ok = False
    for i in range(NM):
        u = U[i]; v = V[i]; ok = u & np.isfinite(v); nv = int(ok.sum())
        if dirn == "bin":
            top = ok & (v == 1); bot = ok & (v == 0); sv = v
        else:
            sv = v if dirn == "high" else -v
            pct = pd.Series(np.where(ok, sv, np.nan)).rank(pct=True, method="average").to_numpy()
            top = ok & (pct > 0.8); bot = ok & (pct <= 0.2)
        ntop = int(top.sum())
        usable = nv >= MIN_VAL and (ntop >= MIN_TOP_BIN if dirn == "bin" else ntop > 0)
        to = np.nan
        if usable and prev_ok and ntop > 0:
            to = 1 - (top & prev_top).sum() / ntop
        r = RM[i]; fr = np.isfinite(r)
        ex = q15 = ic = np.nan
        if usable and np.isfinite(UM[i]) and (top & fr).any():
            ex = r[top & fr].mean() - UM[i]
            if (bot & fr).any():
                q15 = r[top & fr].mean() - r[bot & fr].mean()
            m = ok & fr
            if m.sum() >= 10:
                a = pd.Series(sv[m]).rank().to_numpy(); b = pd.Series(r[m]).rank().to_numpy()
                if a.std() > 0 and b.std() > 0:
                    ic = np.corrcoef(a, b)[0, 1]
        rows.append(dict(form=str(me_dates[i].date()), hold=hold_m[i], seg=seg_m[i], nuni=int(u.sum()), nval=nv, ntop=ntop,
                         ntop_ret=int((top & fr).sum()), usable=usable, turnover=to, excess=ex, q15=q15, ic=ic))
        prev_top, prev_ok = top, usable
    d = pd.DataFrame(rows)
    d["cost_to"] = np.where(d["usable"], d["turnover"].fillna(1.0), np.nan)
    d["net"] = d["excess"] - d["cost_to"] * COST
    return d


def shuffle_V(V, rng):
    S = np.full_like(V, np.nan)
    for i in range(NM):
        ok = U[i] & np.isfinite(V[i])
        idx = np.flatnonzero(ok)
        S[i, idx] = V[i, idx][rng.permutation(len(idx))]
    return S


def summarize_cross(d):
    out = {}
    for sg in ("探索", "確認"):
        x = d[(d.seg == sg) & d.usable & d.excess.notna()]
        out[sg] = dict(n=len(x), ex=boot(x.excess), q15=boot(x.q15), ic=boot(x.ic), net=boot(x.net),
                       to=float(x.turnover.mean()) if x.turnover.notna().any() else np.nan, ntop=float(x.ntop.mean()) if len(x) else np.nan)
    return out


def verdict(c, k):
    b = c["確認"]["ex"]
    if c["確認"]["n"] < MIN_GROUPS:
        return "還沒測"
    if b[f"loB{k}"] > 0:
        return "正向（暫定）"
    if b[f"hiB{k}"] < 0:
        return "負向（暫定）"
    return "分不出"


def label_desc(e_exp, e_con, n_con):
    if n_con < MIN_GROUPS:
        return "還沒測"
    if e_exp["mean"] > 0 and e_con["mean"] > 0 and e_con["lo95"] > 0:
        return "正向，兩段一致"
    if e_exp["mean"] < 0 and e_con["mean"] < 0 and e_con["hi95"] < 0:
        return "負向，兩段一致"
    return "分不出"


def fmt(x, k=4):
    return round(float(x), k) if x is not None and np.isfinite(x) else np.nan


def main():
    snap.check()
    rows, shuf = [], []
    for code, cat, name, typ, dirn in SPEC:
        t1 = time.time()
        base = {"S號": code, "因子": name, "類別": cat, "型別": typ, "方向": "取高"}
        V = pd.read_parquet(os.path.join(FAC, f"{code}.parquet")).reindex(index=U_df.index, columns=sids).to_numpy(float)
        d = cross_series(V, dirn); d.to_csv(os.path.join(OUT_M, f"{code}.csv"), index=False)
        c = summarize_cross(d)
        rng = np.random.default_rng(SEED)
        ds = cross_series(shuffle_V(V, rng), dirn)
        ds.to_csv(os.path.join(OUT_M, f"{code}_shuffle.csv"), index=False)
        cs_ = summarize_cross(ds)
        vd = {k: verdict(c, k) for k in NC}; vs = {k: verdict(cs_, k) for k in NC}
        lab = label_desc(c["探索"]["ex"], c["確認"]["ex"], c["確認"]["n"])
        for sg in ("探索", "確認"):
            z, zs = c[sg], cs_[sg]
            rows.append({**base, "段": sg, "可用月": z["n"], "前組平均檔數": fmt(z["ntop"], 1),
                         "前五分之一月超額": fmt(z["ex"]["mean"], 5), "95%下": fmt(z["ex"]["lo95"], 5), "95%上": fmt(z["ex"]["hi95"], 5),
                         "Bonf68下": fmt(z["ex"]["loB68"], 5), "Bonf68上": fmt(z["ex"]["hiB68"], 5),
                         "Bonf69下": fmt(z["ex"]["loB69"], 5), "Bonf69上": fmt(z["ex"]["hiB69"], 5), "自助法雙尾p(描述)": fmt(z["ex"]["p"], 5),
                         "Q1−Q5": fmt(z["q15"]["mean"], 5), "Q1−Q5_95%下": fmt(z["q15"]["lo95"], 5), "Q1−Q5_95%上": fmt(z["q15"]["hi95"], 5), "Q1−Q5_p": fmt(z["q15"]["p"], 5),
                         "IC平均": fmt(z["ic"]["mean"]), "IC_95%下": fmt(z["ic"]["lo95"]), "IC_95%上": fmt(z["ic"]["hi95"]), "IC_p": fmt(z["ic"]["p"], 5),
                         "換手": fmt(z["to"], 3), "扣成本後超額": fmt(z["net"]["mean"], 5), "扣成本_95%下": fmt(z["net"]["lo95"], 5), "扣成本_95%上": fmt(z["net"]["hi95"], 5),
                         "假訊號_可用月": zs["n"], "假訊號_月超額": fmt(zs["ex"]["mean"], 5), "假訊號_95%下": fmt(zs["ex"]["lo95"], 5), "假訊號_95%上": fmt(zs["ex"]["hi95"], 5),
                         "假訊號_Bonf68下": fmt(zs["ex"]["loB68"], 5), "假訊號_Bonf68上": fmt(zs["ex"]["hiB68"], 5),
                         "假訊號_Bonf69下": fmt(zs["ex"]["loB69"], 5), "假訊號_Bonf69上": fmt(zs["ex"]["hiB69"], 5), "假訊號_p": fmt(zs["ex"]["p"], 5),
                         "假訊號_Q1−Q5": fmt(zs["q15"]["mean"], 5), "假訊號_IC": fmt(zs["ic"]["mean"]), "假訊號_扣成本後": fmt(zs["net"]["mean"], 5),
                         "描述標籤(0053,95%)": lab if sg == "確認" else "",
                         "依門檻落點(確認段,0.05/68)": vd["68"] if sg == "確認" else "", "依門檻落點(確認段,0.05/69)": vd["69"] if sg == "確認" else "",
                         "假訊號落點(0.05/68)": vs["68"] if sg == "確認" else "", "假訊號落點(0.05/69)": vs["69"] if sg == "確認" else ""})
            shuf.append(dict(code=code, seg=sg, mean=zs["ex"]["mean"], lo95=zs["ex"]["lo95"], hi95=zs["ex"]["hi95"],
                             loB68=zs["ex"]["loB68"], hiB68=zs["ex"]["hiB68"], loB69=zs["ex"]["loB69"], hiB69=zs["ex"]["hiB69"], n=zs["n"]))
        print(code, vd, "| shuf", vs, f"{time.time() - t1:.0f}s", flush=True)
    df = pd.DataFrame(rows)
    sh = pd.DataFrame(shuf)
    if ONLY:      # 併入既有結果：只換掉這次跑的格（S30 原「待裁定」列一併覆蓋），其他格原樣保留
        old = pd.read_csv(os.path.join(OUT, "result_add.csv"), dtype=str, encoding="utf-8-sig")
        old = old[~old["S號"].isin(ONLY)]
        df = pd.concat([old, df.astype(object)], ignore_index=True)
        osh = pd.read_csv(os.path.join(OUT_M, "shuffle_cells.csv"), dtype=str)
        sh = pd.concat([osh[~osh["code"].isin(ONLY)], sh], ignore_index=True)
    df["判語採用門檻(seq527)"] = np.where(df["段"].astype(str) == "確認", "0.05/69（最嚴）", "")
    df.to_csv(os.path.join(OUT, "result_add.csv"), index=False, encoding="utf-8-sig")
    sh.to_csv(os.path.join(OUT_M, "shuffle_cells.csv"), index=False)
    con = df[df["段"] == "確認"]
    keep = df[df["S號"].isin(con.loc[con["依門檻落點(確認段,0.05/68)"].astype(str).str.contains("向（暫定）") |
                                        con["依門檻落點(確認段,0.05/69)"].astype(str).str.contains("向（暫定）"), "S號"])]
    keep.to_csv(os.path.join(OUT, "bonf_add.csv"), index=False, encoding="utf-8-sig")
    # 乾跑：所有描述欄檢查（不可有 inf；報酬欄應全 0；計數欄應有值）
    num = pd.DataFrame(rows).select_dtypes("number")
    assert not np.isinf(num.to_numpy()).any(), "有 inf"
    print(df.drop(columns=[c for c in df.columns if c in ("類別", "型別")]).T.to_string())
    print("MODE", MODE, "DATA_LAST", DATA_LAST.date(), "SHA", snap.SHA, f"elapsed {time.time() - t0:.0f}s")
    snap.check()


if __name__ == "__main__":
    main()

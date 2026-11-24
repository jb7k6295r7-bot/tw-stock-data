# -*- coding: utf-8 -*-
"""scan64 step 4：單因子描述掃描的報酬（登錄 回測 0053＋0054、讀法 0134 第三節 1～8、裁定 seq519 §四、seq520）。
讀 scan64/cache/panel.npz（panel.py）、scan64/factors/（factors.py）；方向與因子清單沿用 scan55/freq.py 的 SPEC（頻率表那次已定、看結果前不改）。
輸出 scan64/result.csv、bonf.csv、shuffle_dist.csv、monthly/（逐月序列）。
"""
import os, sys, time, importlib.util
import numpy as np, pandas as pd
import snap
from backtest import data as D
D = snap.fix()

t0 = time.time()
HERE = snap.HERE
FAC = os.path.join(HERE, "factors"); CACHE = os.path.join(HERE, "cache")
OUT_M = os.path.join(HERE, "monthly"); os.makedirs(OUT_M, exist_ok=True)
spec = importlib.util.spec_from_file_location("freq55", os.path.join(os.path.dirname(HERE), "scan55", "freq.py"))
F55 = importlib.util.module_from_spec(spec); spec.loader.exec_module(F55)
SPEC, NOT_THIS = F55.SPEC, F55.NOT_THIS
FREQ = pd.read_csv(os.path.join(os.path.dirname(HERE), "scan55", "freq.csv"), dtype=str).set_index("S號")

EXP = ("2017-03", "2021-12"); CON = ("2022-01", "2026-08")   # 以持有月（橫斷面＝形成月＋1；事件＝進場月）歸段
MIN_VAL, MIN_TOP_BIN, MIN_GROUPS = 50, 5, 24
NCELL = 64
A95 = 0.05
AB = 0.05 / NCELL                 # Bonferroni（seq520）
AEV = 0.05 / (NCELL * 3)          # 事件型 3 個持有期再除 3（執行者保守選擇，見 notes）
B, BLOCK, SEED = 4000, 6, 5
COST = 0.00585
HOLDS = (20, 60, 120)

RUN = [s for s in SPEC if FREQ.loc[s[0], "標籤"] == "可跑"]
assert len(RUN) == NCELL, len(RUN)


def seg_of(s):
    s = str(s)
    if EXP[0] <= s <= EXP[1]:
        return "探索"
    if CON[0] <= s <= CON[1]:
        return "確認"
    return None


# ───────── 價格與報酬 ─────────
P = np.load(os.path.join(CACHE, "panel.npz"))
cal = pd.DatetimeIndex(pd.to_datetime(P["cal"])); sids = [str(s) for s in P["sids"]]
VALID = P["VALID"] == 1
C = P["C"].astype(float); C[~VALID] = np.nan
BAD = np.nan_to_num(P["BAD"]) > 0
T, N = C.shape
Cff = pd.DataFrame(C).ffill().to_numpy()          # 出場：窗內最後一個有效收盤（下市、停牌照最後收盤）
CB = np.vstack([np.zeros((1, N)), np.cumsum(BAD, 0)])
DATA_LAST = cal[np.flatnonzero(VALID.any(1))[-1]]


def win_ret(e, x):
    """e、x：位置陣列（同長）。進場 e 收盤（須有效）→ 出場 x（含）前最後有效收盤；(e, x] 有壞根 ⇒ NaN。"""
    r = Cff[x] / C[e] - 1
    bad = (CB[x + 1] - CB[e + 1]) > 0
    r[bad] = np.nan
    return r


U_df = pd.read_parquet(os.path.join(FAC, "universe.parquet"))
me_dates = pd.DatetimeIndex(pd.to_datetime(U_df.index))
assert list(U_df.columns) == sids
U = U_df.to_numpy(bool)
me_pos = np.array([cal.get_loc(d) for d in me_dates])
NM = len(me_pos)
# 月持有：形成月 i 月底收盤算因子 → 下一交易日收盤買 → 下月最後交易日收盤賣
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

# ───────── 自助法 ─────────
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
    keys = ["mean", "lo95", "hi95", "loB", "hiB", "loEV", "hiEV", "n"]
    if n < 2:
        return dict(zip(keys, [np.nanmean(x) if n else np.nan] + [np.nan] * 6 + [n]))
    m = x[cbb_idx(n)].mean(1)
    q = np.quantile(m, [A95 / 2, 1 - A95 / 2, AB / 2, 1 - AB / 2, AEV / 2, 1 - AEV / 2])
    return dict(zip(keys, [x.mean(), *q, n]))


# ───────── 橫斷面 ─────────
def cross_series(V, dirn):
    """V：NM×N 因子值（已對齊母體欄）。回傳逐月 DataFrame。"""
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
    d["cost_to"] = np.where(d["usable"], d["turnover"].fillna(1.0), np.nan)   # 前月不可用 ⇒ 全買（換手 1）
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


# ───────── 事件 ─────────
RH = {}
for h in HOLDS:
    R = np.full((T, N), np.nan)
    for p in range(T):
        x = D.exit_pos(p, h)
        if x >= T:
            break
        r = Cff[x] / C[p] - 1
        r[(CB[x + 1] - CB[p + 1]) > 0] = np.nan
        R[p] = r
    RH[h] = R
kpos = me_dates.searchsorted(cal, side="left") - 1        # 進場日之前最近一個月底（母體）
BENCH = {}
for h in HOLDS:
    bm = np.full(T, np.nan)
    for p in range(T):
        k = kpos[p]
        if k < 0:
            continue
        m = U[k] & np.isfinite(RH[h][p])
        if m.any():
            bm[p] = RH[h][p][m].mean()
    BENCH[h] = bm
UIDX = [np.flatnonzero(U[k]) for k in range(NM)]
sidx = {s: j for j, s in enumerate(sids)}


def load_events(code):
    e = pd.read_csv(os.path.join(FAC, f"{code}_events.csv"), dtype=str)
    e["entry"] = pd.to_datetime(e["entry_date"])
    e["p"] = cal.get_indexer(e["entry"])
    assert (e["p"] >= 0).all()
    e["k"] = me_dates.searchsorted(e["entry"].values, side="left") - 1
    e["j"] = e["stock_id"].map(sidx)
    e = e[(e.k >= 0) & e.j.notna()].copy(); e["j"] = e.j.astype(int)
    e = e[U[e.k.to_numpy(), e.j.to_numpy()]].copy()
    e["month"] = e["entry"].dt.to_period("M").astype(str)
    e["seg"] = e["month"].map(seg_of)
    return e.sort_values(["p", "j"]).reset_index(drop=True)


def event_excess(e, j=None):
    p = e.p.to_numpy(); j = e.j.to_numpy() if j is None else j
    out = {}
    for h in HOLDS:
        out[h] = RH[h][p, j] - BENCH[h][p]
    return out


def summarize_events(e, X):
    res = {}
    for sg in ("探索", "確認"):
        m = (e.seg == sg).to_numpy()
        res[sg] = {}
        for h in HOLDS:
            x = X[h][m]; mon = e.month.to_numpy()[m]
            ok = np.isfinite(x)
            g = pd.Series(x[ok]).groupby(mon[ok]).mean().sort_index()
            b = boot(g.to_numpy())
            b["n_ev"] = int(ok.sum()); b["ev_mean"] = float(x[ok].mean()) if ok.any() else np.nan
            res[sg][h] = b
    return res


def shuffle_events(e, rng):
    j = np.empty(len(e), int)
    for k, idx in e.groupby("k").indices.items():
        pool = UIDX[k]
        j[idx] = pool[rng.integers(0, len(pool), size=len(idx))]
    return j


# ───────── 判語 ─────────
def verdict_cross(c):
    b = c["確認"]["ex"]
    if c["確認"]["n"] < MIN_GROUPS:
        return "還沒測"
    if b["loB"] > 0:
        return "正向（暫定）"
    if b["hiB"] < 0:
        return "負向（暫定）"
    return "分不出"


def label_desc(e_exp, e_con, n_con):
    """登錄 0053 描述標籤（95%，兩段一致；只描述）。"""
    if n_con < MIN_GROUPS:
        return "還沒測"
    if e_exp["mean"] > 0 and e_con["mean"] > 0 and e_con["lo95"] > 0:
        return "正向，兩段一致"
    if e_exp["mean"] < 0 and e_con["mean"] < 0 and e_con["hi95"] < 0:
        return "負向，兩段一致"
    return "分不出"


def verdict_events(res):
    pos, neg, judged = [], [], []
    for h in HOLDS:
        b = res["確認"][h]
        if b["n"] < MIN_GROUPS:
            continue
        judged.append(h)
        if b["loEV"] > 0:
            pos.append(h)
        elif b["hiEV"] < 0:
            neg.append(h)
    if not judged:
        return "還沒測", ""
    if pos and not neg:
        return "正向（暫定）", "過：" + "/".join(f"{h}日" for h in pos)
    if neg and not pos:
        return "負向（暫定）", "過：" + "/".join(f"{h}日" for h in neg)
    if pos and neg:
        return "分不出", "持有期方向互相矛盾"
    return "分不出", ""


INTEL = {
    "S06": "#13 爆量：測不出", "S18": "#12 個股外資買超比重：測不出", "S19": "#20 投信連買、#30 年底作帳：測不出",
    "S20": "#20 投信連買、#30 年底作帳：測不出", "S23": "#11 融資 20 日增減十分位：融資增最多那 10% +0.80%（方向與常見說法相反）t 3.0 邊緣、沒控制動能",
    "S25": "#22 軋空（券資比高）：測不出", "S28": "#76 敏感度：1,000 張以上同向、CI＞0（描述）",
    "S33": "#9 營收月減−月增 −1.24% t 5.5（過）；#10 月增未創高−月減 +0.90% t 3.6", "S35": "#33B 加速−減速 +1.61% t 2.8 邊緣",
    "S39": "#15 EPS 單季季增−季減 +1.60% t 7.1（過）；情報比上一季、本表比去年同季", "S40": "#15 毛利率升−降 +1.44% t 5.9（過）；情報比上一季、本表比去年同季",
    "S47": "#36 存貨那格測不出", "S48": "#36 應收增速−營收增速 ≥30pp（60 天）−2.48% t 2.5 邊緣",
    "S61": "#31 除息後填息：測不出（題目不同，只當相關）", "S63": "#5 出處置：測不出", "S91": "#31 除息後填息：測不出",
}


def fmt(x, k=4):
    return round(float(x), k) if x is not None and np.isfinite(x) else np.nan


def main():
    snap.check()
    rows, shuf = [], []
    for code, cat, name, typ, dirn, rule, defn in RUN:
        t1 = time.time()
        base = {"S號": code, "因子": name, "類別": cat, "型別": typ,
                "方向": {"high": "取高", "low": "取低", "bin": "條件成立", "event": "事件"}[dirn] + ("（早交）" if code == "S70" else "")}
        if typ == "橫斷面":
            V = pd.read_parquet(os.path.join(FAC, f"{code}.parquet")).reindex(index=U_df.index, columns=sids).to_numpy(float)
            d = cross_series(V, dirn); d.to_csv(os.path.join(OUT_M, f"{code}.csv"), index=False)
            c = summarize_cross(d)
            rng = np.random.default_rng(SEED)
            ds = cross_series(shuffle_V(V, rng), dirn if dirn != "bin" else "bin")
            cs_ = summarize_cross(ds)
            vd = verdict_cross(c); vs = verdict_cross(cs_)
            lab = label_desc(c["探索"]["ex"], c["確認"]["ex"], c["確認"]["n"])
            for sg in ("探索", "確認"):
                z, zs = c[sg], cs_[sg]
                rows.append({**base, "段": sg, "可用月或事件群": z["n"], "前組平均檔數": fmt(z["ntop"], 1),
                             "前五分之一月超額": fmt(z["ex"]["mean"], 5), "95%下": fmt(z["ex"]["lo95"], 5), "95%上": fmt(z["ex"]["hi95"], 5),
                             "Bonf下": fmt(z["ex"]["loB"], 5), "Bonf上": fmt(z["ex"]["hiB"], 5),
                             "Q1−Q5": fmt(z["q15"]["mean"], 5), "Q1−Q5_95%下": fmt(z["q15"]["lo95"], 5), "Q1−Q5_95%上": fmt(z["q15"]["hi95"], 5),
                             "IC平均": fmt(z["ic"]["mean"]), "IC_95%下": fmt(z["ic"]["lo95"]), "IC_95%上": fmt(z["ic"]["hi95"]),
                             "換手": fmt(z["to"], 3), "扣成本後超額": fmt(z["net"]["mean"], 5), "扣成本_95%下": fmt(z["net"]["lo95"], 5), "扣成本_95%上": fmt(z["net"]["hi95"], 5),
                             "假訊號_可用月": zs["n"], "假訊號_月超額": fmt(zs["ex"]["mean"], 5), "假訊號_95%下": fmt(zs["ex"]["lo95"], 5), "假訊號_95%上": fmt(zs["ex"]["hi95"], 5),
                             "假訊號_Bonf下": fmt(zs["ex"]["loB"], 5), "假訊號_Bonf上": fmt(zs["ex"]["hiB"], 5),
                             "假訊號_Q1−Q5": fmt(zs["q15"]["mean"], 5), "假訊號_IC": fmt(zs["ic"]["mean"]), "假訊號_扣成本後": fmt(zs["net"]["mean"], 5),
                             "描述標籤(0053,95%)": lab if sg == "確認" else "", "判語(確認段,Bonf 0.05/64)": vd if sg == "確認" else "",
                             "假訊號判語": vs if sg == "確認" else ""})
            for sg in ("探索", "確認"):
                zs = cs_[sg]["ex"]
                shuf.append(dict(code=code, typ="橫斷面", seg=sg, h="月", mean=zs["mean"], lo95=zs["lo95"], hi95=zs["hi95"], loB=zs["loB"], hiB=zs["hiB"], n=zs["n"],
                                 pass95=bool(zs["lo95"] > 0 or zs["hi95"] < 0), passB=bool(zs["loB"] > 0 or zs["hiB"] < 0)))
        else:
            e = load_events(code)
            X = event_excess(e)
            r = summarize_events(e, X)
            rng = np.random.default_rng(SEED)
            js = shuffle_events(e, rng)
            Xs = event_excess(e, js)
            rs = summarize_events(e, Xs)
            vd, why = verdict_events(r); vs, _ = verdict_events(rs)
            labs = "；".join(f"{h}日:" + label_desc(r["探索"][h], r["確認"][h], r["確認"][h]["n"]) for h in HOLDS)
            ev = pd.DataFrame({"stock_id": e.stock_id, "entry": e.entry_date, "month": e.month, "seg": e.seg, "kind": e.kind,
                               **{f"x{h}": X[h] for h in HOLDS}, **{f"shuf{h}": Xs[h] for h in HOLDS}})
            ev.to_csv(os.path.join(OUT_M, f"{code}_events_excess.csv.gz"), index=False, compression="gzip")
            extra = ""
            if code in ("S72", "S74"):
                subs = [("first20", "20 交易日內首次")] if code == "S72" else [("gain", "取得資格"), ("loss", "喪失資格")]
                parts = []
                for kd, nm in subs:
                    m = (e.kind == kd).to_numpy()
                    e2 = e[m].reset_index(drop=True); X2 = {h: X[h][m] for h in HOLDS}
                    r2 = summarize_events(e2, X2)
                    parts.append(nm + "：" + "，".join(
                        f"{sg}{h}日 {r2[sg][h]['mean'] * 100:+.2f}%〔{r2[sg][h]['lo95'] * 100:+.2f}～{r2[sg][h]['hi95'] * 100:+.2f}〕群{r2[sg][h]['n']}"
                        for sg in ("探索", "確認") for h in HOLDS))
                extra = "；".join(parts) + "（只描述、不判）"
            for sg in ("探索", "確認"):
                row = {**base, "段": sg, "可用月或事件群": "／".join(str(r[sg][h]["n"]) for h in HOLDS)}
                for h in HOLDS:
                    z, zs = r[sg][h], rs[sg][h]
                    row.update({f"事件{h}日_超額": fmt(z["mean"], 5), f"事件{h}日_95%下": fmt(z["lo95"], 5), f"事件{h}日_95%上": fmt(z["hi95"], 5),
                                f"事件{h}日_Bonf下": fmt(z["loB"], 5), f"事件{h}日_Bonf上": fmt(z["hiB"], 5),
                                f"事件{h}日_判語區間下(0.05/192)": fmt(z["loEV"], 5), f"事件{h}日_判語區間上(0.05/192)": fmt(z["hiEV"], 5),
                                f"事件{h}日_群數": z["n"], f"事件{h}日_事件數": z["n_ev"], f"事件{h}日_事件加權平均": fmt(z["ev_mean"], 5),
                                f"假訊號{h}日_超額": fmt(zs["mean"], 5), f"假訊號{h}日_95%下": fmt(zs["lo95"], 5), f"假訊號{h}日_95%上": fmt(zs["hi95"], 5),
                                f"假訊號{h}日_判語區間下(0.05/192)": fmt(zs["loEV"], 5), f"假訊號{h}日_判語區間上(0.05/192)": fmt(zs["hiEV"], 5)})
                row.update({"描述標籤(0053,95%)": labs if sg == "確認" else "", "判語(確認段,Bonf 0.05/64)": (vd + (f"（{why}）" if why else "")) if sg == "確認" else "",
                            "假訊號判語": vs if sg == "確認" else "", "附註描述": extra if sg == "確認" else ""})
                rows.append(row)
                for h in HOLDS:
                    zs = rs[sg][h]
                    shuf.append(dict(code=code, typ="事件", seg=sg, h=h, mean=zs["mean"], lo95=zs["lo95"], hi95=zs["hi95"], loB=zs["loB"], hiB=zs["hiB"],
                                     loEV=zs["loEV"], hiEV=zs["hiEV"], n=zs["n"],
                                     pass95=bool(zs["lo95"] > 0 or zs["hi95"] < 0), passB=bool(zs["loB"] > 0 or zs["hiB"] < 0),
                                     passEV=bool(zs["loEV"] > 0 or zs["hiEV"] < 0)))
        print(code, rows[-1].get("判語(確認段,Bonf 0.05/64)"), "| shuf", rows[-1].get("假訊號判語"), f"{time.time() - t1:.0f}s", flush=True)
    for code, cat, name, typ, dirn, rule, defn in SPEC:
        if FREQ.loc[code, "標籤"] != "可跑":
            rows.append({"S號": code, "因子": name, "類別": cat, "型別": typ, "段": "—", "判語(確認段,Bonf 0.05/64)": FREQ.loc[code, "標籤"],
                         "附註描述": "不跑、不計 N（seq520）" + ("；⛔ 不改口徑（官方漲跌停價）" if code == "S83" else "")})
    for code, cat, name, why in NOT_THIS:
        rows.append({"S號": code, "因子": name, "類別": cat, "段": "—", "判語(確認段,Bonf 0.05/64)": "沒資料", "附註描述": f"登錄列為不在這次（{why}）"})
    df = pd.DataFrame(rows)
    df["情報〈四十一〉對照（口徑不同、並列不覆蓋）"] = df["S號"].map(INTEL).fillna("")
    df.to_csv(os.path.join(HERE, "result.csv"), index=False, encoding="utf-8-sig")
    vcol = "判語(確認段,Bonf 0.05/64)"
    bon = df[(df["段"] == "確認") & df[vcol].astype(str).str.contains("向（暫定）")]
    keep = df[df["S號"].isin(bon["S號"])]
    keep.to_csv(os.path.join(HERE, "bonf.csv"), index=False, encoding="utf-8-sig")
    sh = pd.DataFrame(shuf); sh.to_csv(os.path.join(OUT_M, "shuffle_cells.csv"), index=False)
    qs = [0, 0.025, 0.05, 0.25, 0.5, 0.75, 0.95, 0.975, 1]
    out = []
    for (typ, sg, h), g in sh.groupby(["typ", "seg", "h"], sort=False):
        r = {"型別": typ, "段": sg, "持有": h, "格數": len(g)}
        for q in qs:
            r[f"超額q{q}"] = round(float(g["mean"].quantile(q)), 5)
        r["95%看起來有方向格數"] = int(g.pass95.sum()); r["Bonf(0.05/64)看起來有方向格數"] = int(g.passB.sum())
        if typ == "事件":
            r["判語區間(0.05/192)看起來有方向格數"] = int(g.passEV.sum())
        out.append(r)
    # 64 個假訊號判語（確認段，與真因子同規則）
    con = df[df["段"] == "確認"]
    out.append({"型別": "全部64格", "段": "確認", "持有": "判語同規則", "格數": len(con),
                "Bonf(0.05/64)看起來有方向格數": int(con["假訊號判語"].astype(str).str.contains("向（暫定）").sum())})
    pd.DataFrame(out).to_csv(os.path.join(HERE, "shuffle_dist.csv"), index=False, encoding="utf-8-sig")
    print(con[vcol].value_counts().to_dict())
    print("shuffle verdicts", con["假訊號判語"].value_counts().to_dict())
    print("DATA_LAST", DATA_LAST.date(), "SHA", snap.SHA, f"elapsed {time.time() - t0:.0f}s")
    snap.check()


if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
"""researchRev_win 的獨立查核（⛔ 不 import researchRev_win、researchRev；訊號迴圈借用 researchRev_check 的逐根寫法）。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python backtest/researchRev_win_check.py [--n 40]

① 格：從 win_cell_x.csv.gz 自己算 平均、月／20 日區段 CR0、n_eff、k（兩層各自：訊號×版本×視窗 n_eff ≥ 10）、Bonferroni CI、出口、判定、扣成本後 ⇒ 對 win_cells.csv
② 個股基準②：從 win_stock_days.csv.gz 自己排十分位（每天、同值依代號序）⇒ 對 dec；每個 H 的 (月, 分位) 平均 ⇒ 用它重算事件的 X ⇒ 對 win_cell_x（逐格排序後逐值）
③ 大盤：逐根迴圈重偵測 13 種簡單訊號（主快照 0050）⇒ 每個 H：窗 [w0, w1−H]、合併 20、T＋1 開盤有效 ⇒ 原版基準日與 R_H 對 win_events_market
④ 個股逐檔：抽 n 檔 × 9 種簡單訊號 × H ∈ {5, 60}：窗、母體月（panel_ext）、合併、剔除、R_H ⇒ 對 win_events_stock
⑤ 穩不穩：照裁定 seq249 讀法自己重寫 ⇒ 對 win_cells.csv
"""
from __future__ import annotations
import argparse, json, math, os, sys
from statistics import NormalDist
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest")); sys.path.insert(0, os.path.expanduser("~/tw-p17"))
import researchRev_check as RC               # 逐根迴圈訊號（獨立寫法）、0050 接序列、merge、lastvalid
H2, D, TR, MF = RC.H2, RC.D, RC.TR, RC.MF
OUT = os.path.expanduser("~/tw-p17/backtest/resultsRev")
HS = (5, 10, 20, 60)
COST = 0.00585
HIGH = RC.HIGH


def judge(x, g, z, high):
    x = np.asarray(x, float); n = len(x)
    if n == 0:
        return {"n_eff": 0, "判定": "不可判定"}
    m, se, ng = RC.cr0(x, g); ne = min(n, ng)
    if ne < 10:
        return {"n_eff": ne, "mean": m, "判定": "不可判定"}
    lo, hi = m - z * se, m + z * se
    rs = "—（樣本不足以分辨）" if ne < 30 else ("結果①" if lo <= 0 <= hi else ("結果③" if m < 0 else "結果②"))
    ok = rs == ("結果③" if high else "結果②")
    sh = COST if high else -COST
    okn = ok and ((hi + sh < 0) if high else (lo + sh > 0))
    return {"n_eff": ne, "mean": m, "lo": lo, "hi": hi, "判定": "通過" if ok else "不通過", "扣成本後": "仍過" if okn else ("不過" if ok else "—")}


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--n", type=int, default=40); a = ap.parse_args()
    errs = []; info = {}
    C = pd.read_csv(os.path.join(OUT, "win_cells.csv")); X = pd.read_csv(os.path.join(OUT, "win_cell_x.csv.gz"), dtype={"g": str})
    # ① 格
    for lay in ("大盤", "個股"):
        xs = X[X["層"] == lay]
        grp = {k: g for k, g in xs.groupby(["code", "版", "H"])}
        ne = {k: min(len(g), g["g"].nunique()) for k, g in grp.items()}
        k = sum(1 for v in ne.values() if v >= 10)
        z = NormalDist().inv_cdf(1 - (0.05 / k) / 2)
        info[f"k_{lay}"] = k
        for r in C[C["層"] == lay].itertuples():
            g = grp.get((r.code, r.版, r.H))
            j = judge(g["X"].to_numpy(float) if g is not None else [], g["g"].to_numpy() if g is not None else [], z, r.code in HIGH)
            if j["判定"] != r.判定 or (j.get("扣成本後", "—") != (r.扣成本後 if isinstance(r.扣成本後, str) else "—")):
                errs.append(f"格 {lay} {r.code} {r.版} H{r.H}：判定 {j['判定']}／{j.get('扣成本後')} vs {r.判定}／{r.扣成本後}")
            if "mean" in j and abs(j["mean"] - r.mean) > 1e-12:
                errs.append(f"格 {lay} {r.code} {r.版} H{r.H} 平均")
    # ② 個股基準②
    DD = pd.read_csv(os.path.join(OUT, "win_stock_days.csv.gz"), dtype={"sid": str})
    dec = np.full(len(DD), -1, int)
    for d, g in DD.groupby("d"):
        ok = g[np.isfinite(g["r20p"])].sort_values(["r20p", "sid"], kind="mergesort")
        dec[ok.index.to_numpy()] = (np.arange(len(ok)) * 10) // len(ok)
    if (dec != DD["dec"].to_numpy()).any():
        errs.append(f"十分位不一致 {(dec != DD['dec'].to_numpy()).sum()} 列")
    cal = D.load_calendar(); mon = np.array([str(x)[:7] for x in cal])
    DD["m"] = mon[DD["d"].to_numpy()]; DD["dec2"] = dec
    key = {(s, int(d)): int(q) for s, d, q in zip(DD["sid"], DD["d"], dec)}
    E = pd.read_csv(os.path.join(OUT, "win_events_stock.csv.gz"), dtype={"sid": str})
    for H in HS:
        f = DD[np.isfinite(DD[f"R{H}"]) & (DD["dec2"] >= 0)]
        B2 = f.groupby(["m", "dec2"])[f"R{H}"].mean()
        e = E[E["H"] == H]
        for code in sorted(e["code"].unique()):
            ec = e[e["code"] == code]
            for ver, stc, bc, rc in (("原版", "st", "T", "R"), ("確認版", "st_c", "C", "Rc")):
                k_ = ec[ec[stc] == "保留"]
                b2 = np.array([B2.get((mon[int(d)], key.get((s, int(d)), -1)), np.nan) for s, d in zip(k_["sid"], k_[bc])], float)
                x = np.sort((k_[rc].to_numpy(float) - b2)[np.isfinite(b2)])
                got = np.sort(X[(X["層"] == "個股") & (X["code"] == code) & (X["版"] == ver) & (X["H"] == H)]["X"].to_numpy(float))
                if len(x) != len(got) or (len(x) and np.max(np.abs(x - got)) > 1e-12):
                    errs.append(f"個股 X {code} {ver} H{H}：{len(x)} vs {len(got)}")
    # ③ 大盤
    main_, _ = RC.m0050()
    lo, hi = main_["dates"].index(RC.W0), main_["dates"].index(RC.W1)
    ev, b = RC.series_events(main_, RC.SIMPLE)
    EM = pd.read_csv(os.path.join(OUT, "win_events_market.csv.gz"))
    nm = 0
    for H in HS:
        for code in RC.SIMPLE:
            T = RC.merge([t for t in ev[code] if lo <= t <= hi - H])
            T = [t for t in T if np.isfinite(main_["o"][t + 1])]
            mine = [main_["dates"][t] for t in T]
            got = EM[(EM["code"] == code) & (EM["版"] == "原版") & (EM["H"] == H)]
            if mine != got["基準日"].tolist():
                errs.append(f"大盤 {code} H{H} 事件不一致 {len(mine)} vs {len(got)}")
                continue
            r = [main_["c"][RC.lastvalid(main_["c"], t + H)] / main_["o"][t + 1] - 1 for t in T]
            if len(r) and np.max(np.abs(np.array(r) - got["R"].to_numpy(float))) > 1e-12:
                errs.append(f"大盤 {code} H{H} R 不一致")
            nm += len(r)
    info["大盤逐筆"] = nm
    # ④ 個股逐檔
    from backtest import p4_features as P4F
    p = P4F.read_panel(os.path.expanduser("~/tw-p17/backtest/resultsp9_engine/panel_ext.csv.gz"))
    p = p[p["eligible"].astype(bool)]
    elig = p.groupby("stock_id")["measure_date"].apply(lambda s: set(str(x)[:7] for x in s)).to_dict()
    w0, w1 = int(cal.searchsorted(pd.Timestamp(RC.W0))), int(cal.searchsorted(pd.Timestamp(RC.W1)))
    off = TR.load_official(); rng = np.random.default_rng(13)
    sids = sorted(E["sid"].unique()); pick = [sids[i] for i in rng.choice(len(sids), size=min(a.n, len(sids)), replace=False)]
    mkt = E.drop_duplicates("sid").set_index("sid")["market"]; ns = 0
    for sid in pick:
        st = D.load_stock(sid, mkt[sid], cal); df = st.df
        o, h, l, c, v = (df[k].to_numpy(float) for k in ("open", "high", "low", "close", "volume"))
        valid = np.isfinite(c); bb = np.flatnonzero(valid)
        evs = RC.loop_signals(*[[float(x) for x in arr[bb]] for arr in (o, h, l, c, v)], RC.STOCK_SIMPLE)
        tlf = {int(bb[t]): int(bb[f]) for t, f in evs["_TLF"].items()}
        tb = TR.one(sid, cal); ds = TR.delist_status({sid: tb}, cal, official=off).get(sid)
        dl = ds is not None and ds["status"].startswith("delisted")
        pb = np.zeros(len(cal), bool)
        for b_ in D.breakpoints(df, st.event_dates):
            if b_["rule"] in ("price", "price+gap"):
                pb[b_["pos"]] = True
        g5 = MF._g5(valid, upto=ds["last"]) if dl else MF._g5(valid)
        SS = {"cs_pb": np.cumsum(pb).astype(np.int32), "cs_g5": np.cumsum(g5).astype(np.int32)}
        em = elig.get(sid, set())
        for H in (5, 60):
            for code in RC.STOCK_SIMPLE:
                T = RC.merge([t for t in (int(bb[x]) for x in evs[code]) if w0 <= t <= w1 - H and mon[t] in em])
                mine = []
                for t in T:
                    f0 = tlf[t] if code == "H_TL" else t
                    bad = H2.brk(SS, f0, t + H) or (not tb["trd"][t + 1]) or (not np.isfinite(o[t + 1])) or tb["up_o"][t + 1] or tb["dn_o"][t + 1]
                    if not bad:
                        mine.append((t, c[RC.lastvalid(c, t + H)] / o[t + 1] - 1))
                got = E[(E["sid"] == sid) & (E["code"] == code) & (E["H"] == H) & (E["st"] == "保留")]
                if [t for t, _ in mine] != got["T"].astype(int).tolist():
                    errs.append(f"個股 {sid} {code} H{H} 事件不一致 {len(mine)} vs {len(got)}")
                elif len(mine) and max(abs(x - y) for (_, x), y in zip(mine, got["R"].to_numpy(float))) > 1e-12:
                    errs.append(f"個股 {sid} {code} H{H} R 不一致")
                ns += len(mine)
    info["個股逐檔檔數"] = len(pick); info["個股逐檔事件"] = ns
    # ⑤ 穩不穩
    for (lay, code, ver), g in C.groupby(["層", "code", "版"]):
        g = g.set_index("H")
        high = code in HIGH
        passed = [H for H in HS if g.at[H, "判定"] == "通過"]
        for H in passed:
            i = HS.index(H); nb = [HS[j] for j in (i - 1, i + 1) if 0 <= j < len(HS)]
            same = all(np.isfinite(g.at[x, "mean"]) and ((g.at[x, "mean"] < 0) if high else (g.at[x, "mean"] > 0)) for x in nb)
            lab = g.at[H, "穩不穩"]
            if same != ("⇒ 穩" in lab and f"{H} 天通過" in lab) or ((not same) and f"只在 {H} 天看得到" not in lab):
                errs.append(f"穩不穩 {lay} {code} {ver} H{H}：{lab}")
    info["錯誤數"] = len(errs)
    print(json.dumps(info, ensure_ascii=False))
    for e_ in errs[:25]:
        print("  ⛔", e_)
    json.dump({"info": info, "errors": errs[:300]}, open(os.path.join(OUT, "win_check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("查核：" + ("全過" if not errs else f"⛔ {len(errs)} 項不過"))


if __name__ == "__main__":
    main()

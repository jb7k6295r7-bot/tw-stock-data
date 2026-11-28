# -*- coding: utf-8 -*-
"""scanadd：S59 興櫃轉上櫃 頻率表（⛔ 不算任何報酬、超額）。
名單：tw-stock-data data/meta/emerging_to_otc/emerging_to_otc.csv（凍結 sha256 00101a75…aac84，裁定 seq526／529）。
兩種讀法並列（登錄 0053「事件後下一交易日收盤買」＋0134 讀法 3「事件只計進場前最近月底在母體內」）：
  A 字面：事件日＝日線第一個 tpex 交易日；進場＝下一交易日；須在進場前最近月底母體內。
  B 同 S58 實作：第一次進入當年母體的月底（距第一個 tpex 交易日 ≤550 天）；進場＝下一交易日。
另報與 S58（同快照重建）的重疊。輸出 ~/scanadd/s59/。"""
import os, sys, hashlib, json
import numpy as np, pandas as pd
import snap
import factors as F
D = snap.fix()
snap.check()
LIST = os.path.expanduser("~/s59/emerging_to_otc.csv")
SHA_FROZEN = "00101a7581612213fc01988988416be3324f09d6f8abd83c7270f424142aac84"
assert hashlib.sha256(open(LIST, "rb").read()).hexdigest() == SHA_FROZEN
OUT = os.path.join(snap.BASE, "s59"); os.makedirs(OUT, exist_ok=True)
L = pd.read_csv(LIST, dtype=str)
inf = L[L.inferred == "1"].copy()
U_df = pd.read_parquet(os.path.join(F.FAC, "universe.parquet"))
U = U_df.to_numpy(bool); me = pd.DatetimeIndex(pd.to_datetime(U_df.index)); usids = list(U_df.columns)
assert usids == F.sids
col = {s: j for j, s in enumerate(F.sids)}
cal = F.cal; T = len(cal); LAST = cal[-1]
H = (20, 60, 120)


def first_tpex(s):
    p = os.path.join(D.DATA, "stocks", f"{s}.csv")
    if not os.path.exists(p):
        return None
    x = pd.read_csv(p, dtype=str, usecols=["date", "market"])
    x = x[x.market == "tpex"]
    return pd.Timestamp(x.date.iloc[0]) if len(x) else None


def seg_of(d):
    m = d.to_period("M")
    if pd.Period("2017-03") <= m <= pd.Period("2021-12"):
        return "探索"
    if pd.Period("2022-01") <= m <= pd.Period("2026-08"):
        return "確認"
    return ""


def nxt(d):
    p = int(cal.searchsorted(d, side="right"))
    return cal[p] if p < T else None


def last_me_before(d):
    k = int(me.searchsorted(d, side="left")) - 1
    return k if k >= 0 else None


rows = []; miss = []
for _, r in inf.iterrows():
    s = r.stock_id
    ft = first_tpex(s)
    if ft is None:
        miss.append((s, r.irb170_ym, "日線無 tpex 列")); continue
    same = str(ft.to_period("M")) == r.irb170_ym
    j = col.get(s)
    # A
    eA = nxt(ft); kA = last_me_before(eA) if eA is not None else None
    inA = bool(j is not None and kA is not None and U[kA, j])
    # B
    tB = eB = None
    if j is not None:
        k0 = int(me.searchsorted(ft, side="left"))
        ks = [k for k in np.flatnonzero(U[:, j]) if k >= k0]
        if ks and (me[ks[0]] - ft).days <= 550:
            tB = me[ks[0]]; eB = nxt(tB)
    rows.append(dict(stock_id=s, irb170_ym=r.irb170_ym, first_tpex=ft.date(), same_month=same, in_panel=j is not None,
                     A_entry=eA.date() if eA is not None else None, A_in_universe=inA,
                     B_form=tB.date() if tB is not None else None, B_entry=eB.date() if eB is not None else None))
ev = pd.DataFrame(rows); ev.to_csv(os.path.join(OUT, "s59_events_both.csv"), index=False)
pd.DataFrame(miss, columns=["stock_id", "irb170_ym", "原因"]).to_csv(os.path.join(OUT, "s59_missing.csv"), index=False)

# S58（同快照，照 factors.misc_events 原式重建；只為重疊）
FS_ = F.FS_
s58 = set()
for j, s in enumerate(F.sids):
    fs = pd.Timestamp(FS_[j])
    if fs <= pd.Timestamp("2015-03-01"):
        continue
    rr = np.flatnonzero(U[:, j])
    if len(rr) == 0:
        continue
    t = me[rr[0]]
    if (t - fs).days > 550:
        continue
    s58.add((s, nxt(t).date()))


def freq(entries):
    out = {}
    for sg in ("探索", "確認"):
        e = [d for d in entries if seg_of(pd.Timestamp(d)) == sg]
        out[f"事件{sg}"] = len(e)
        for h in H:
            ok = []
            for d in e:
                p = int(cal.searchsorted(pd.Timestamp(d)))
                if p + h - 1 <= T - 1:
                    ok.append(pd.Timestamp(d).to_period("M"))
            out[f"群數{sg}_{h}日"] = len(set(ok))
    return out


A = [d for d, k in zip(ev.A_entry, ev.A_in_universe) if k and d is not None]
B = [d for d in ev.B_entry if d is not None]
Bset = {(s, d) for s, d in zip(ev.stock_id, ev.B_entry) if d is not None}
s58_seg = {x for x in s58 if seg_of(pd.Timestamp(x[1]))}
B_seg = {x for x in Bset if seg_of(pd.Timestamp(x[1]))}
res = dict(名單sha=SHA_FROZEN, 資料sha=snap.SHA, 資料最後日=str(LAST.date()), 推定筆數=len(inf),
           日線找不到tpex=len(miss), 上櫃首日與IRB170同月=int(ev.same_month.sum()), 在面板=int(ev.in_panel.sum()),
           A=freq(A), B=freq(B),
           S58=freq([d for _, d in s58]),
           重疊=dict(B在S58=len(B_seg & s58_seg), B事件_兩段=len(B_seg), S58事件_兩段=len(s58_seg),
                     B佔S58=round(len(B_seg & s58_seg) / max(len(s58_seg), 1), 3)))
json.dump(res, open(os.path.join(OUT, "s59_freq.json"), "w"), ensure_ascii=False, indent=1, default=str)
print(json.dumps(res, ensure_ascii=False, indent=1, default=str))
# 每月事件數（B），只描述
mb = pd.Series([pd.Timestamp(d).to_period("M") for d in B]).value_counts().sort_index()
mb.to_csv(os.path.join(OUT, "s59_B_monthly.csv"))
snap.check()

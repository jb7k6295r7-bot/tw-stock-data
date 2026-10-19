# -*- coding: utf-8 -*-
"""VIX 飆高配 QLD（使用者看過 researchVIXbuy／researchVIXentry 結果後追加「vix 配 qld 呢？」）。回測線計算子代理。
⛔ 描述，不是買賣建議；⛔ 不計 N、不判合格、不是登錄件；看過前兩份結果才追加 ⇒ 結果句必附
   「樣本極少」「QLD 含兩倍槓桿與每日重設耗損，那斯達克集中科技股」「合成段非實際 ETF」。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchVIXqld
    查核：cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchVIXqld_check

═══ 讀法（寫於 2026-10-20，台北）═══
 Q0 只換標的、⛔ 不改定義：表 A ＝ researchVIXbuy.run_market 原函式（B1～B6，門檻 30／40／50／75 段起日隔天開盤買，3 個月～5 年、
    勝率、對同窗全部日超額、段內與 1 年內最深再跌、回本交易日）；表 B ＝ researchVIXentry.run／summarize／table 原函式（≥40 段 E1～E5，
    1 年／3 年期末財富、對 E1 差、買進後最深再跌、帳面最深）。兩支與 researchUSC13、researchUSA1_data 皆只 import、⛔ 一行未改。
 Q1 QLD 真實價：researchUSA1_data.load_market 的 QLD（Yahoo adjclose÷close 還原開收；資料快照 60d2f99），2006-06-21 起；
    時差、DTB3 現金、成本 0.05% 同 ^SP500TR（researchVIXentry.mk_us 原式）。
 Q2 合成 QLD（⚠ 合成、非實際 ETF）：researchUSA1_data.synth(M, "QLD", SPREAD)（A1 seq3 逐字：r_L ＝ 2 r_QQQ含息 −（DTB3_{t−1}/100＋0.25%）/252 − 0.95%/252；
    開盤 ＝ 前收 ×（1＋2×隔夜跳空））⇒ 與 researchUSC11L_m 合成 SSO 同一支函式、同參數，只換 kind。
    指數腿 ＝ QQQ 含息價（1999-03-10 起）；⚠ 私有庫沒有 ^NDX（macro/ 只有 QQQ、QLD、TQQQ）⇒ 1999-03 以前「無資料」；
    依 A1 seq3「⛔ 不用 ^NDX 價格指數代」亦不外補。⚠ QQQ 自身含 0.20% 費用 ⇒ 合成 QLD 略被多扣。全段用合成（含 2006-06 之後）。
 Q3 對照：QQQ（1 倍，含息）、^SP500TR、SSO 真實、合成 SSO（A.synth "SSO"）。全期的 ^SP500TR（表 A、B）、SSO／合成 SSO（表 B）
    先從 resultsVIXbuy／resultsVIXentry 既有結果讀，並在本檔重算一次核對（重現差寫入 json）。
 Q4 窗：⭐ 不同標的資料起點不同、平常日分布也不同 ⇒ 除了「各自全期」，另列兩個同窗（所有標的同一段、同一組觸發）：
    W1 ＝ 合成 QLD 首個有效開盤日起（1999-03-11）；W2 ＝ QLD 與 SSO 真實首個有效開盤日中較晚者起（2006-06-21）。
    表 A 窗 ＝ run_market 的 lo 參數（段只取 VIX 日 ≥ lo、全部日母體 ≥ lo）；⭐ 先驗證「lo 起算的段」＝「全歷史段中段起日 ≥ lo 者」
    （逐門檻段起、段止相同），否則中止。表 B 窗 ＝ d_first 覆寫為窗起日（run 原式：段起日 ＜ d_first ⇒ 無資料；所屬 ≥30 段起日 ＜ d_first ⇒ E5 無資料）。
 Q5 合成 vs 真實 QLD 對帳（描述）：2006-06-21～2026-09-30 逐曆年報酬差（合成 − 真實；2006、2026 為部分年）、全期年化差、日報酬相關。
⛔⛔ 私有資料：resultsVIXqld/ 只放彙總（平均、中位、勝率、勝負次數、最深中位／最差）與觸發日（VIX 為 FRED 公開，不含價格）；
   美股逐段明細、逐年報酬放 ~/us_work/vixqld/。
"""
from __future__ import annotations

import json
import os
import time

import numpy as np
import pandas as pd

from backtest import researchUSC13 as C
from backtest import researchUSA1_data as A
from backtest import researchVIXbuy as VB
from backtest import researchVIXentry as VE

OUT = os.path.expanduser("~/tw-p17/backtest/resultsVIXqld")
WORK = os.path.expanduser("~/us_work/vixqld")
SEED = 20261020
DISC = "描述，不是買賣建議；樣本極少；QLD 含兩倍槓桿與每日重設耗損，那斯達克集中科技股；合成段非實際 ETF；看過前兩份結果才追加"
HA = (3, 6, 12, 36)       # 表 A 列出的持有期（json 另含 5 年）


def first_ok(X):
    return str(X["dates"][int(np.flatnonzero(X["ok"])[0])])


def seg_check(vd, vv, lo):
    """Q4：lo 起算的段 ＝ 全歷史段中段起日 ≥ lo 者。"""
    bad = []
    for thr in VB.THRS:
        a = [(g["段起日"], g["段止日（VIX≤20）"]) for g in C.segments(vd, vv, thr, lo)]
        b = [(g["段起日"], g["段止日（VIX≤20）"]) for g in C.segments(vd, vv, thr, None) if g["段起日"] >= lo]
        if a != b:
            bad.append({"門檻": thr, "lo起算": a[:3], "全歷史過濾": b[:3]})
    return bad


def yearly(dates, c, d0):
    """d0 起每曆年（首年由 d0 收盤、末年到資料末）收盤報酬。"""
    i0 = int(np.searchsorted(dates, d0))
    s = pd.Series(c[i0:], index=pd.to_datetime(dates[i0:]))
    s = s[np.isfinite(s.to_numpy())]
    out = {}
    prev = float(s.iloc[0])
    for y, g in s.groupby(s.index.year):
        out[int(y)] = float(g.iloc[-1] / prev - 1); prev = float(g.iloc[-1])
    return out


def main():
    T0 = time.time()
    os.makedirs(OUT, exist_ok=True); os.makedirs(WORK, exist_ok=True)
    vd, vv, vinfo = C.load_vix()
    U = C.load_us(); M = U["M"]
    QLo, QLc = A.synth(M, "QLD", A.SPREAD)
    SLo, SLc = A.synth(M, "SSO", A.SPREAD)
    LEVN = "QLD 含兩倍槓桿與每日重設耗損，那斯達克集中科技股"
    XS = {"QLD": VE.mk_us(U, M["O"]["QLD"], M["C"]["QLD"], "QLD 真實（那斯達克100 兩倍）", note=LEVN),
          "合成QLD": VE.mk_us(U, QLo, QLc, "合成 QLD（⚠ 合成、非實際 ETF）", note="A1 seq3 式；QQQ 含息 ×2；" + LEVN),
          "QQQ": VE.mk_us(U, M["O"]["QQQ"], M["C"]["QQQ"], "QQQ（1 倍，含息）", note="那斯達克集中科技股"),
          "SP500TR": VE.mk_us(U, U["o"], U["cf"], "^SP500TR"),
          "SSO": VE.mk_us(U, M["O"]["SSO"], M["C"]["SSO"], "SSO 真實（標普兩倍）", note="正二含槓桿與每日重設耗損"),
          "合成SSO": VE.mk_us(U, SLo, SLc, "合成 SSO（⚠ 合成、非實際 ETF）", note="A1 seq3 式；正二含槓桿與每日重設耗損")}
    F = {k: first_ok(X) for k, X in XS.items()}
    W1 = F["合成QLD"]; W2 = max(F["QLD"], F["SSO"])
    WINS = [("各自全期", None, list(XS)),
            (f"同窗 W1（{W1} 起）", W1, ["合成QLD", "QQQ", "SP500TR", "合成SSO"]),
            (f"同窗 W2（{W2} 起，QLD 上市後）", W2, ["QLD", "合成QLD", "QQQ", "SP500TR", "SSO", "合成SSO"])]
    res = {"題": "VIX 飆高配 QLD：表 A（researchVIXbuy 定義）與表 B（researchVIXentry 定義）只換標的（描述）",
           "聲明": DISC + "；⛔ 不計 N、不判合格", "讀法": "Q0～Q5 見 researchVIXqld.py docstring",
           "標的首個有效開盤日": F, "^NDX": "私有庫無資料（macro/ 只有 QQQ、QLD、TQQQ）⇒ 合成 QLD 從 QQQ 1999-03-10 起；依 A1 seq3 不以價格指數代",
           "窗": {w: (lo or "各自資料首日") for w, lo, _ in WINS}}
    # Q4 段一致性
    sc = {}
    for lo in sorted({F[k] for k in XS} | {W1, W2}):
        if lo > vd[0]:
            sc[lo] = seg_check(vd, vv, lo)
    res["段一致性（lo 起算 ＝ 全歷史過濾）"] = {k: ("一致" if not v else v) for k, v in sc.items()}
    assert all(not v for v in sc.values()), sc

    # ═════ 表 A ═════
    rng = np.random.default_rng(SEED)
    A_res = {}; evs = []; LA = []
    for wn, wlo, keys in WINS:
        A_res[wn] = {}
        for k in keys:
            X = XS[k]
            lo = wlo if wlo else (F[k] if F[k] > vd[0] else None)
            summ, ev = VB.run_market(X, vd, vv, lo, X["label"], rng)
            A_res[wn][k] = summ
            for r in ev:
                r = dict(r); r.pop("_b", None); r["窗"] = wn; evs.append(r)
    res["表A"] = A_res
    pd.DataFrame(evs).to_csv(os.path.join(WORK, "VIXqld_A_events.csv"), index=False, encoding="utf-8", float_format="%.6f")
    # 重現：^SP500TR 各自全期 ＝ VIXbuy.json（確定性欄位）
    JB = json.load(open(os.path.expanduser("~/tw-p17/backtest/resultsVIXbuy/VIXbuy.json"), encoding="utf-8"))
    mx = 0.0
    for thr in VB.THRS:
        a = A_res["各自全期"]["SP500TR"][f"≥{thr:.0f}"]; b = JB["美股"][f"≥{thr:.0f}"]
        for hm in VB.HM:
            h = VB.HN[hm]
            for kk in ("平均", "中位", "勝率"):
                for grp in ("觸發組", "全部日"):
                    x, y = a[h][grp][kk], b[h][grp][kk]
                    if x is not None or y is not None:
                        mx = max(mx, abs(x - y))
        for kk in ("中位", "最差"):
            mx = max(mx, abs(a["段內最深"][kk] - b["段內最深"][kk]), abs(a["1年內最深"][kk] - b["1年內最深"][kk]))
    res["重現_表A_^SP500TR對VIXbuy.json_最大差"] = mx

    def rowA(lbl, S, thr):
        cells = []
        for h in HA:
            c = S[VB.HN[h]]
            if c["觸發組"]["n"] == 0:
                cells.append("—"); continue
            cells.append(f"{VB.fmt(c['觸發組']['平均'])} (n{c['觸發組']['n']}, 勝{c['觸發組']['勝率']:.0%}, 超額{VB.fmt(c['超額平均（觸發−全部日）'])})")
        return (f"≥{thr:.0f}{'（樣本極少）' if thr >= 50 else ''} | {lbl} | {S['段數']} | " + " | ".join(cells) +
                f" | {VB.fmt(S['段內最深']['中位'])}/{VB.fmt(S['段內最深']['最差'])} | {VB.fmt(S['段內最深_回本交易日']['中位'], False)}/{VB.fmt(S['段內最深_回本交易日']['最長'], False)}"
                f"（未回本 {S['段內最深_回本交易日']['未回本段數']}）"
                f" | {VB.fmt(S['1年內最深']['中位'])}/{VB.fmt(S['1年內最深']['最差'])} | {VB.fmt(S['1年內最深_回本交易日']['中位'], False)}/{VB.fmt(S['1年內最深_回本交易日']['最長'], False)}"
                f"（未回本 {S['1年內最深_回本交易日']['未回本段數']}）")
    for wn, wlo, keys in WINS:
        LA.append(f"## 表 A｜{wn}（{DISC}）")
        LA.append("門檻 | 標的 | 段數 | " + " | ".join(VB.HN[h] for h in HA) +
                  " | 段內最深 中位/最差 | 回本交易日 中位/最長 | 1年內最深 中位/最差 | 回本交易日 中位/最長")
        for thr in VB.THRS:
            for k in keys:
                LA.append(rowA(XS[k]["label"], A_res[wn][k][f"≥{thr:.0f}"], thr))
        for k in keys:
            base = A_res[wn][k]["≥30"]
            LA.append(f"全部日 | {XS[k]['label']}（{A_res[wn][k]['隨機對照母體']['首日']} 起）| — | " +
                      " | ".join(f"{VB.fmt(base[VB.HN[h]]['全部日']['平均'])} (勝{base[VB.HN[h]]['全部日']['勝率']:.0%})" for h in HA) + " | — | — | — | —")
        LA.append("")

    # ═════ 表 B ═════
    B_res = {}; LB = []; segs_all = []
    for wn, wlo, keys in WINS:
        B_res[wn] = {}
        for k in keys:
            X = dict(XS[k])
            if wlo:
                X["d_first"] = wlo
            df, skipped, nseg = VE.run(X, vd, vv)
            S = VE.summarize(df)
            B_res[wn][k] = {"≥40段數（期間內）": nseg, "無資料段": skipped, "彙總": S}
            LB += [f"### 表 B｜{wn}"] + VE.table(X["label"], S, nseg, skipped, X.get("note", ""))
            df["窗"] = wn; segs_all.append(df)
    res["表B"] = B_res
    SA = pd.concat(segs_all, ignore_index=True)
    SA.to_csv(os.path.join(WORK, "VIXqld_B_segments.csv"), index=False, encoding="utf-8", float_format="%.6f")
    # 重現：各自全期 ^SP500TR／SSO／合成 SSO ＝ VIXentry.json
    JE = json.load(open(os.path.expanduser("~/tw-p17/backtest/resultsVIXentry/VIXentry.json"), encoding="utf-8"))
    mp = {"SP500TR": "美股 ^SP500TR", "SSO": "美股 SSO（真實 2 倍）", "合成SSO": "美股 合成 SSO（⚠ 合成、非實際 ETF）"}
    mx = 0.0
    for k, lbl in mp.items():
        a = B_res["各自全期"][k]["彙總"]; b = JE["標的"][lbl]["彙總"]
        for h in ("1年", "3年"):
            for m in VE.METH:
                for kk in ("期末財富平均（萬）", "期末財富中位（萬）", "買進後最深再跌_中位", "買進後最深再跌_最差", "帳面最深_最差"):
                    mx = max(mx, abs(a[h][m][kk] - b[h][m][kk]))
    res["重現_表B_^SP500TR／SSO／合成SSO對VIXentry.json_最大差"] = mx
    # 觸發日（公開）：每個 ≥40 段的 d0 與各標的在各窗是否有資料
    trig = SA[(SA["方式"] == "E1") & (SA["持有"] == "1年")][["窗", "標的", "段起日d0", "段起VIX", "段內最高VIX", "段止日", "E2第二筆依據", "E3回落<30日", "E5的≥30段起日"]]
    trig.to_csv(os.path.join(OUT, "VIXqld_triggers.csv"), index=False, encoding="utf-8")

    # ═════ Q5 合成 vs 真實 QLD ═════
    dates = U["dates"]
    yr_r = yearly(dates, M["C"]["QLD"], F["QLD"]); yr_s = yearly(dates, QLc, F["QLD"])
    yr_q = yearly(dates, M["C"]["QQQ"], F["QLD"])
    yd = {y: yr_s[y] - yr_r[y] for y in yr_r}
    i0 = int(np.searchsorted(dates, F["QLD"])); i1 = len(dates) - 1
    while not np.isfinite(M["C"]["QLD"][i1]):
        i1 -= 1
    yrs = (pd.Timestamp(str(dates[i1])) - pd.Timestamp(str(dates[i0]))).days / 365.25
    cr = (M["C"]["QLD"][i1] / M["C"]["QLD"][i0]) ** (1 / yrs) - 1; cs = (QLc[i1] / QLc[i0]) ** (1 / yrs) - 1
    rr = M["C"]["QLD"][i0 + 1:i1 + 1] / M["C"]["QLD"][i0:i1] - 1; rs = QLc[i0 + 1:i1 + 1] / QLc[i0:i1] - 1
    mk = np.isfinite(rr) & np.isfinite(rs)
    res["合成vs真實QLD"] = {"期間": f"{dates[i0]}～{dates[i1]}（{yrs:.2f} 年；2006、2026 為部分年）",
                          "逐年差（合成−真實）": yd, "逐年差_絕對值平均": float(np.mean(np.abs(list(yd.values())))),
                          "逐年差_最大絕對": float(max(np.abs(list(yd.values())))),
                          "年化：真實": float(cr), "年化：合成": float(cs), "年化差（合成−真實）": float(cs - cr),
                          "日報酬相關": float(np.corrcoef(rr[mk], rs[mk])[0, 1]), "日報酬差_標準差（年化）": float(np.std(rs[mk] - rr[mk]) * np.sqrt(252))}
    pd.DataFrame({"年": list(yr_r), "真實QLD": [yr_r[y] for y in yr_r], "合成QLD": [yr_s[y] for y in yr_r],
                  "QQQ": [yr_q.get(y) for y in yr_r]}).to_csv(os.path.join(WORK, "VIXqld_yearly.csv"), index=False, encoding="utf-8", float_format="%.6f")
    # QLD 資料檢查：還原日報酬極端值
    rq = M["C"]["QLD"][1:] / M["C"]["QLD"][:-1] - 1
    ext = [(str(dates[i + 1]), float(rq[i])) for i in np.flatnonzero(np.abs(rq) > 0.3)]
    res["資料"] = {"VIX": vinfo, "美股快照": A.data_commit(), "QLD": M["audit"]["QLD"], "QQQ": M["audit"]["QQQ"],
                 "QLD 還原日報酬 |r|>30% 的日子（斷點檢查）": ext}
    res["精簡表A"] = LA; res["精簡表B"] = LB
    res["算於"] = C.now_tpe(); res["秒"] = round(time.time() - T0)
    VE.jdump(res, os.path.join(OUT, "VIXqld.json"))
    open(os.path.join(OUT, "VIXqld_tableA.txt"), "w", encoding="utf-8").write("\n".join(LA))
    open(os.path.join(OUT, "VIXqld_tableB.txt"), "w", encoding="utf-8").write("\n".join(LB))
    print("\n".join(LA)); print("\n".join(LB))
    print(json.dumps({k: res[k] for k in ("標的首個有效開盤日", "段一致性（lo 起算 ＝ 全歷史過濾）", "重現_表A_^SP500TR對VIXbuy.json_最大差",
                                           "重現_表B_^SP500TR／SSO／合成SSO對VIXentry.json_最大差", "合成vs真實QLD", "資料")}, ensure_ascii=False, indent=1, default=str))
    return res


if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
"""PREREG營量出場 seq3：資料網頁（使用者 09-28「調資料我看一下」；⛔ 只描述、不改任何判定）。回測線，2026-09-28。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchYLexit3_view

數字：總表、甲 9 格、乙 18 格、放棄原因、買回次數分佈 ＝ resultsYLexit3（cells.csv、summary.json）原值；
逐筆明細 ＝ 主世界、種子 0、挑中格（甲 營量_甲3_b5_H40、乙 營量_乙3_k55_c10_C120）在自己組合裡【實際成交】、確認段（2022-01-03～2026-08-24）進場的每一筆，取自引擎 audit；
  本規則淨 ＝ 賣出金額 ÷ 買進金額 − 1 − 0.585%（甲的暫出再進成本已在合成路徑內）；原版淨 ＝ 同一筆訊號照營量 v1（60 天）g_H60 − 0.585%
例子（使用者 09-28 追加「多筆一點」；⛔ 不看圖挑）：按情況分類、每類 4 筆：2 筆照規則（該類「差 ＝ 本規則 − 原版」最高、最低各 1）＋ 2 筆隨機（default_rng([20260928, 族, 類序])，從其餘筆不放回抽）；不足 4 筆 ⇒ 全列
  甲 類：沒觸發／警訊放棄／10 天放棄／買回上限放棄／買回後（未放棄）比原版好／比原版差（另有「暫出未買回、到期結束」只報占比）
  乙 類：多抱比原版好／比原版差／與原版相同；圖一律 <details>，每類第 1 張預設展開
查核：三個組合種子 0 權益 ＝ resultsYLexit3 seeds.csv（eq_sha）；抽 10 筆明細：audit 淨報酬 ＝ 路徑自算 g − 成本；挑中格確認段年化 ＝ cells.csv
輸出 backtest/resultsYLexit3/view/營量出場seq3資料_20260928.html、trades_seed0.csv、check.json
"""
from __future__ import annotations

import hashlib
import html
import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import data as D
from backtest import rerun17 as RR
from backtest import research11 as R11
from backtest import researchYLexit as YX
from backtest import researchYLexit3 as Y3
from backtest import chart_svg as CS

OUT = "backtest/resultsYLexit3/view"
F_HTML = "營量出場seq3資料_20260928.html"
COST = R11.COST
C0, C1 = "2022-01-03", "2026-08-24"


def sha(eq):
    return hashlib.sha256(np.asarray(eq, float).tobytes()).hexdigest()[:16]


def P(x, d=2):
    return "—" if x is None or (isinstance(x, float) and not np.isfinite(x)) else f"{x * 100:+.{d}f}%"


def cls(x):
    return "pos" if x > 0 else ("neg" if x < 0 else "")


def trades(aud):
    op = {}; rows = []
    for a in sorted(aud, key=lambda z: (z["t"], z["side"] != "sell")):
        if a["side"] == "buy":
            op[a["sid"]] = a
        else:
            b = op.pop(a["sid"])
            rows.append({"key": a["sid"], "t_in": b["t"], "t_out": a["t"], "淨": a["amt"] / b["amt"] - 1 - a["cost"] / b["amt"]})
    for k, b in op.items():
        rows.append({"key": k, "t_in": b["t"], "t_out": None, "淨": np.nan})
    return pd.DataFrame(rows)


def yi_detail(W, s, k, K, cs, C):
    idx, o, c, nb, _, _ = YX.bars_of(W, s); n = len(idx); nbk = nb[max(0, k - 20)]
    ke = k + 1; kk = ke + K - 1; kc = ke + C - 1
    if kk > n - 1 or kk >= nbk:
        return None
    B0 = Bv = c[kk]; ups = 0; last = min(kc, n - 1, nbk - 1)
    for j in range(kk + 1, last + 1):
        if c[j] < Bv:
            return {"kk": kk, "B0": B0, "BF": Bv, "ups": ups, "why": "跌破基準"}
        if (j - kk) % cs == 0 and c[j] >= Bv:
            ups += int(c[j] > Bv); Bv = c[j]
    return {"kk": kk, "B0": B0, "BF": Bv, "ups": ups, "why": "觸頂上限" if last == kc else "資料尾／斷點"}


def main():
    os.makedirs(OUT, exist_ok=True)
    S = json.load(open("backtest/resultsYLexit3/summary.json", encoding="utf-8"))
    PT = pd.read_csv("backtest/resultsYLexit3/cells.csv")
    SE = pd.read_csv("backtest/resultsYLexit3/seeds.csv.gz", dtype={"eq_sha": str}, low_memory=False)
    J = S["判定"]; Z = S["0050"]
    pj, py = J["甲"]["挑中"], J["乙"]["挑中"]
    # ── 主世界（researchYLexit3.main 同一套）
    from backtest import researchT1fix as T1
    ctx = T1.build_ctx(True)
    cal = ctx["cal"]; mk = ctx["mk"]; AND = RR._G["AND"]
    SF = R11.stop_force_days(R11.valid_from_data(sorted(ctx["closes"]), mk, cal), ctx["w1"])
    SEGP = {sg: (int(cal.searchsorted(pd.Timestamp(x))), int(cal.searchsorted(pd.Timestamp(y)))) for sg, (x, y) in YX.SEG_C.items()}
    W = {"cal": cal, "NP": ctx["ncal"], "closes": ctx["closes"], "opens": ctx["opens"], "SF": SF, "mk": mk, "w0": ctx["w0"], "w1": ctx["w1"], "SEGP": SEGP,
         "BARS": {}, "EVD": {}, "REV": Y3.rev_events(os.path.join(RR.OUT, "sig_edc6f", "panel_rev.csv.gz"))}
    W["SIGH"] = {("營量", 60): ctx["sig13"]}
    bj = int(pj.split("_b")[1].split("_")[0]) / 100; Hj = int(pj.split("_H")[1].split("_")[0])
    Ky = int(py.split("_k")[1].split("_")[0]); cy = int(py.split("_c")[1].split("_")[0]); Cy = int(py.split("_C")[1])
    if Hj != 60:
        t_, _ = YX.exits_H(W, ctx["sig13"], Hj); W["SIGH"][("營量", Hj)] = t_[t_[f"xpos_H{Hj}"] >= 0]
    W["NEWK"] = {"營量": {s: set(g["k"].astype(int)) for s, g in AND.groupby("sid")}}
    Y3._W["主"] = W
    CJ = ("營量", "甲", (bj, Hj, Y3.WS, 10, 1)); CY = ("營量", "乙", (Ky, cy, Cy)); CB = ("營量", "base", None)
    CK = {}; TR = {}
    for cell in (CB, CJ, CY):
        sig, rule, cl, op, sf, hm = Y3.inputs(W, cell)
        o, aud = YX._eng(W, "營量", sig, rule, 7000, closes=cl, opens=op, SF=sf, held_map=hm)
        ref = SE[(SE["世界"] == "主") & (SE["格"] == Y3.cname(cell)) & (SE["r"] == 0)]["eq_sha"].iloc[0]
        CK[f"種子0 權益 ＝ seeds.csv（{Y3.cname(cell)}）"] = bool(sha(o["equity"]) == ref)
        eq = np.asarray(o["equity"], float); x, y = SEGP["確認"]
        c_, m_, _ = RR.win_metrics(eq, o["first"], o["end"], x, y)
        CK[f"確認段年化 ＝ cells.csv（{Y3.cname(cell)}）"] = bool(abs(c_ - PT.set_index("格").loc[Y3.cname(cell), "確認_年化"]) < 1e-15)
        TR[cell] = trades(aud)
    t0c = int(cal.searchsorted(pd.Timestamp(C0))); t1c = int(cal.searchsorted(pd.Timestamp(C1)))
    base = ctx["sig13"].reset_index(drop=True)
    orig = {(s, int(e)): (int(x), float(g), int(k)) for s, e, x, g, k in zip(base["sid"], base["entry_pos"], base["xpos_H60"], base["g_H60"], base["k"])}
    uni = D.load_universe().set_index("stock_id")["name"]
    NM = lambda s: str(uni.get(s, ""))
    dt = lambda t: str(cal[int(t)].date()) if t is not None and 0 <= int(t) < len(cal) else "資料尾"
    op_ = ctx["opens"]; cl_ = ctx["closes"]
    # ── 甲逐筆
    jsig = Y3.inputs(W, CJ)[0]; jst = {(st["sid"], int(st["e"])): st for st in W["JST"][CJ]}
    gmap = {(u, int(e)): (int(x), float(g)) for u, e, x, g in zip(jsig["usid"], jsig["entry_pos"], jsig[f"xpos_H{Hj}"], jsig[f"g_H{Hj}"])}
    jt = TR[CJ]; jt = jt[(jt["t_in"] >= t0c) & (jt["t_in"] <= t1c)].copy(); jt["sid"] = jt["key"].str.split("#").str[0]
    JR = []
    for r in jt.itertuples():
        s = r.sid; e = int(r.t_in); st = jst[(s, e)]; x0, g0, k = orig[(s, e)]; xr, gr = gmap[(s, e)]
        idx = YX.bars_of(W, s)[0]; nre = st["進站回"] + st["進新訊號"]; ev = []
        for i_, (sb, rb, pc) in enumerate(st["段"]):
            ts = int(idx[sb]); ev.append(("賣", ts, float(op_[s][ts])))
            if i_ < nre:
                tb = int(idx[rb]); ev.append(("買回", tb, float(op_[s][tb])))
        if st["放棄"]:
            why = f"放棄（{st['放棄']}{'：' + '、'.join(st['警訊']) if st['警訊'] else ''}）"
            fin = ("放棄釋出", st["釋出t"])
        elif st["終於暫出"]:
            why = "第 H 天結束（仍在外）"; fin = ("結束", r.t_out)
        elif st["出"]:
            why = "第 H 天結束（已買回）"; fin = ("結束", r.t_out)
        else:
            why = "沒觸發、第 H 天結束"; fin = ("結束", r.t_out)
        JR.append({"sid": s, "名稱": NM(s), "t_in": e, "進場價": float(op_[s][e]), "事件": ev, "結果": why, "出場t": fin[1], "出": st["出"], "買回": nre,
                   "規則淨": r.淨, "路徑淨": (gr - COST) if r.t_out == xr else np.nan, "原版淨": g0 - COST, "段": st["段"], "終於暫出": st["終於暫出"], "放棄": st["放棄"], "xr": xr, "x0": x0})
    J_ = pd.DataFrame(JR); J_["差"] = J_["規則淨"] - J_["原版淨"]
    # ── 乙逐筆
    ysig = Y3.inputs(W, CY)[0]; info, _ = W["YST"][CY]
    ymap = {(s, int(e)): (int(x), float(g), float(h)) for s, e, x, g, h in zip(ysig["sid"], ysig["entry_pos"], ysig["xpos_H60"], ysig["g_H60"], info["held"])}
    yt = TR[CY]; yt = yt[(yt["t_in"] >= t0c) & (yt["t_in"] <= t1c)].copy()
    YR = []
    for r in yt.itertuples():
        s = r.key; e = int(r.t_in); x0, g0, k = orig[(s, e)]; xr, gr, hd = ymap[(s, e)]
        d_ = yi_detail(W, s, k, Ky, cy, Cy)
        idx = YX.bars_of(W, s)[0]
        YR.append({"sid": s, "名稱": NM(s), "t_in": e, "進場價": float(op_[s][e]), "基準日t": int(idx[d_["kk"]]) if d_ else None, "基準0": d_["B0"] if d_ else np.nan,
                   "最終基準": d_["BF"] if d_ else np.nan, "上調": d_["ups"] if d_ else 0, "結果": d_["why"] if d_ else "第 k 天前結束（照原版）", "出場t": r.t_out,
                   "持有天數": hd, "規則淨": r.淨, "路徑淨": (gr - COST) if r.t_out == xr else np.nan, "原版淨": g0 - COST, "xr": xr, "x0": x0, "k": k})
    Y_ = pd.DataFrame(YR); Y_["差"] = Y_["規則淨"] - Y_["原版淨"]
    # 查核：抽 10 筆
    rng = np.random.default_rng(20260928)
    samp = pd.concat([J_.dropna(subset=["路徑淨"]).sample(5, random_state=1), Y_.dropna(subset=["路徑淨"]).sample(5, random_state=1)])
    CK["抽 10 筆：audit 淨報酬 ＝ 路徑自算 g − 成本（最大差）"] = float((samp["規則淨"] - samp["路徑淨"]).abs().max())
    CK["逐筆全部（排程出場者）：audit ＝ 路徑（最大差）"] = float(max((J_["規則淨"] - J_["路徑淨"]).abs().max(), (Y_["規則淨"] - Y_["路徑淨"]).abs().max()))
    CK["全過"] = bool(all(v is True for k_, v in CK.items() if isinstance(v, bool)) and CK["逐筆全部（排程出場者）：audit ＝ 路徑（最大差）"] < 1e-12)
    # 例子（分類、每類 4 筆）
    J_["類"] = np.select([J_["出"] == 0, J_["放棄"] == "警訊", J_["放棄"] == "等滿10", J_["放棄"] == "買回上限", (J_["買回"] > 0) & (J_["差"] > 0), J_["買回"] > 0],
                        ["沒觸發", "警訊放棄", "10 天放棄", "買回上限放棄", "買回後比原版好", "買回後比原版差"], "暫出未買回、到期結束")
    Y_["類"] = np.where(Y_["差"] > 0, "多抱比原版好", np.where(Y_["差"] < 0, "多抱比原版差", "與原版相同"))
    CATS = {"甲": ["沒觸發", "警訊放棄", "10 天放棄", "買回上限放棄", "買回後比原版好", "買回後比原版差"], "乙": ["多抱比原版好", "多抱比原版差", "與原版相同"]}
    PICK = []
    for fam, G_ in (("甲", J_), ("乙", Y_)):
        for ci, cat in enumerate(CATS[fam]):
            g = G_[G_["類"] == cat]
            if not len(g):
                continue
            chosen = []
            if len(g) <= 4:
                chosen = [(i, "全列") for i in g.sort_values("t_in").index]
            else:
                imax = g["差"].idxmax(); imin = g["差"].idxmin()
                chosen = [(imax, "規則：差（本規則−原版）最高"), (imin, "規則：差（本規則−原版）最低")]
                if g["差"].max() == g["差"].min():                      # 整類差距相同 ⇒ 改取進場最早、最晚
                    gs_ = g.sort_values("t_in"); imax, imin = gs_.index[0], gs_.index[-1]
                    chosen = [(imax, "規則：本類差（本規則−原版）都相同、取進場最早"), (imin, "規則：本類差都相同、取進場最晚")]
                rest = [i for i in g.sort_values("t_in").index if i not in (imax, imin)]
                rr = np.random.default_rng([20260928, 1 if fam == "甲" else 2, ci]).choice(len(rest), size=2, replace=False)
                chosen += [(rest[int(j)], f"隨機（種子 [20260928, {1 if fam == '甲' else 2}, {ci}]）") for j in rr]
            PICK += [(fam, cat, i, how) for i, how in chosen]
    bad_dir = []
    for fam, cat, i, how in PICK:
        G_ = J_ if fam == "甲" else Y_; g = G_[G_["類"] == cat]
        if "最高" in how and G_.at[i, "差"] != g["差"].max():
            bad_dir.append((fam, cat, "最高"))
        if "最低" in how and G_.at[i, "差"] != g["差"].min():
            bad_dir.append((fam, cat, "最低"))
    CK["例子挑法方向 ＝ 標籤（最高／最低）不符"] = bad_dir
    ab_bad = [int(i) for fam, cat, i, how in PICK if fam == "甲" and ((J_.at[i, "放棄"] if isinstance(J_.at[i, "放棄"], str) else None) is not None) != (cat in ("警訊放棄", "10 天放棄", "買回上限放棄"))]
    CK["例子：「放棄」標籤只出現在三種放棄類（不符筆）"] = ab_bad
    CK["全過"] = bool(CK["全過"] and not bad_dir and not ab_bad)
    # ── CSV
    J_.drop(columns=["段"]).assign(事件=J_["事件"].map(lambda z: "｜".join(f"{a} {dt(t)} {p:.2f}" for a, t, p in z))).to_csv(os.path.join(OUT, "trades_jia_seed0.csv"), index=False, float_format="%.10g")
    Y_.to_csv(os.path.join(OUT, "trades_yi_seed0.csv"), index=False, float_format="%.10g")
    json.dump(CK, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    # ── HTML
    CSS = open("backtest/list_yl13_hist.py", encoding="utf-8").read().split('CSS = """')[1].split('"""')[0]
    CSS += "\n.pick{background:#fff4cc}.late{background:#e8f4ff}th.s{cursor:pointer;text-decoration:underline dotted}td.l,th.l{text-align:left}.small{font-size:.8rem}"
    JS = """<script>
function srt(th){const t=th.closest('table'),i=[...th.parentNode.children].indexOf(th),b=t.tBodies[0],rs=[...b.rows];
const d=th.dataset.d==='a'?'d':'a';th.dataset.d=d;rs.sort((x,y)=>{let p=x.cells[i].dataset.v??x.cells[i].textContent,q=y.cells[i].dataset.v??y.cells[i].textContent;
let a=parseFloat(p),c=parseFloat(q);if(!isNaN(a)&&!isNaN(c))return d==='a'?a-c:c-a;return d==='a'?p.localeCompare(q):q.localeCompare(p)});rs.forEach(r=>b.appendChild(r));}
</script>"""
    H = ['<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">',
         "<title>營量出場 seq3 資料</title>", f"<style>{CSS}</style>{JS}</head><body><main id='top'>", "<h1>營量 v1 出場兩件（seq3）：資料</h1>"]
    one = (f"兩件都<b>不合格</b>、對營量 v1 <b>分不出</b>。甲（跌破成本暫出；有警訊、等滿 10 天或買回過一次就換下一檔）挑中 {pj}："
           f"確認段 {P(J['甲']['確認_年化'])}；乙（續抱確認、基準每 {cy} 天上調）挑中 {py}：確認段 {P(J['乙']['確認_年化'])}；營量 v1 {P(PT.set_index('格').loc['營量v1','確認_年化'])}、0050 {P(Z['確認']['cagr'])}。")
    H.append(f"<p class='lead'>{one}</p><p class='note'>⛔ 只是描述，判定照報告（resultsYLexit3/REPORT.md）。報酬都扣 0.585%。還原價。"
             "先驗提醒：本專案停損類（營飆停損、回測 研究五／六、四類單獨）全部不如抱著。甲件含使用者 09-28 追加「買回次數最多一次，超過換下檔」。</p>")
    H.append("<nav class='toc'><a href='#s1'>1 總表</a><a href='#s2'>2 甲 9 格</a><a href='#s3'>3 乙 18 格</a><a href='#s4'>4 甲放棄原因／買回次數</a>"
             "<a href='#s5'>5 逐筆明細</a><a href='#s6'>6 K 線例子</a></nav>")
    T = PT.set_index("格")

    def seg3(r):
        return "".join(f"<td>{P(r[f'{sg}_年化'])}／{P(r[f'{sg}_回落'])}</td><td>{r[f'{sg}_標籤']}</td>" for sg in ("探索", "確認", "早年"))
    H.append("<h2 id='s1'>1 總表</h2><div class='wrap'><table><tr><th class='l'>項目</th><th>探索 17-21</th><th>標籤</th><th>確認 22-26</th><th>標籤</th><th>早年 12-14</th><th>標籤</th></tr>")
    for nm, lab in ((pj, "甲 挑中"), (py, "乙 挑中"), ("營量v1", "營量 v1")):
        H.append(f"<tr><td class='l'>{lab}<br><span class='small'>{nm}</span></td>{seg3(T.loc[nm])}</tr>")
    H.append("<tr><td class='l'>0050</td>" + "".join(f"<td>{P(Z[sg]['cagr'])}／{P(Z[sg]['mdd'])}</td><td>—</td>" for sg in ("探索", "確認", "早年")) + "</tr></table></div>")
    H.append(f"<p class='note'>件標籤＝確認、早年較嚴：甲 {J['甲']['件標籤']}、乙 {J['乙']['件標籤']}。對營量 v1：甲 {J['甲']['對營量v1']}；乙 {J['乙']['對營量v1']}。</p>")

    def grid(fam, keys, title, sid):
        H.append(f"<h2 id='{sid}'>{title}</h2><div class='wrap'><table><tr>{keys}<th>探索</th><th>標籤</th><th>確認</th><th>標籤</th><th>早年</th><th>標籤</th><th>確認配對差〔95% CI〕</th><th>早年配對差</th></tr>")
        for r in PT[PT["件"] == fam].to_dict("records"):
            c = "pick" if r["格"] in (pj, py) else ("late" if (r["確認_標籤"] == "合格" and fam == "乙") else "")
            nm = r["格"].split("_", 2)[2].replace("_", " ")
            H.append(f"<tr class='{c}'><td class='l'>{nm}{' ★挑中' if c == 'pick' else (' ◆事後合格' if c == 'late' else '')}</td>{seg3(r)}"
                     f"<td>{P(r['確認_配對差年化'])}〔{P(r['確認_配對差lo'])}, {P(r['確認_配對差hi'])}〕</td><td>{P(r['早年_配對差年化'])}</td></tr>")
        H.append("</table></div>")
    grid("甲", "<th class='l'>b、H</th>", "2 甲 9 格（b × H）", "s2")
    H.append("<p class='note'>★＝探索段挑中（先合格、再比值）。配對差＝本格減營量 v1 同段日報酬差，年化。</p>")
    grid("乙", "<th class='l'>k、c、C</th>", "3 乙 18 格（k × c × C）", "s3")
    H.append("<p class='note'>★＝探索段挑中；◆＝確認段事後看合格、但不是探索段挑的，⛔ 不能當結論。C120 與 C250 幾乎相同：基準上調後都在上限前出場。</p>")
    ps = S["路徑必報"]["主|甲"]; pe = S["路徑必報"]["早年|甲"]
    H.append("<h2 id='s4'>4 甲 放棄原因與買回次數（挑中格）</h2><div class='wrap'><table><tr><th class='l'>項目</th><th>主窗 2017-2026</th><th>早年</th></tr>")
    for k_ in ("筆", "有暫出的筆比例", "放棄原因：警訊", "放棄原因：等滿10", "放棄原因：買回上限", "警訊含 W1（筆）", "警訊含 W2（筆）", "警訊含 W3（筆）", "警訊含 W4（筆）",
               "有暫出者：最後站回（結束時在場）比例", "買回：站回（次）", "買回：新訊號（次）"):
        f_ = lambda v: f"{v:.1%}" if isinstance(v, float) else str(v)
        H.append(f"<tr><td class='l'>{k_}</td><td>{f_(ps[k_])}</td><td>{f_(pe[k_])}</td></tr>")
    H.append("</table></div><p class='note'>W1 下跌放量｜W2 高檔爆量長黑｜W3 帶量跌破 MA50｜W4 新公布月營收年增 ＜ 0（同一筆可同時含多種）。</p>")
    H.append("<div class='wrap'><table><tr><th>每筆買回次數</th><th>有上限 1（判定）主</th><th>沒上限（seq3 原文）主</th><th>有上限 早年</th><th>沒上限 早年</th></tr>")
    ks = sorted({int(k) for d in (ps["每筆買回次數分佈（有上限 1）"], ps["每筆買回次數分佈（沒上限，seq3 原文）"]) for k in d})
    for k_ in ks:
        g = lambda d: d.get(str(k_), d.get(k_, 0))
        H.append(f"<tr><td>{k_}</td><td>{g(ps['每筆買回次數分佈（有上限 1）'])}</td><td>{g(ps['每筆買回次數分佈（沒上限，seq3 原文）'])}</td>"
                 f"<td>{g(pe['每筆買回次數分佈（有上限 1）'])}</td><td>{g(pe['每筆買回次數分佈（沒上限，seq3 原文）'])}</td></tr>")
    H.append("</table></div>")
    # 5 逐筆
    H.append(f"<h2 id='s5'>5 逐筆明細（確認段進場、種子 0、實際成交；點表頭可排序）</h2><h3>甲 {pj}（{len(J_)} 筆）</h3>"
             "<div class='wrap'><table><thead><tr>" + "".join(f"<th class='s{' l' if i_ in (0, 1, 4) else ''}' onclick='srt(this)'>{h}</th>" for i_, h in enumerate(
                 ["代號", "名稱", "進場日", "進場價", "賣出／買回（日期 價格）", "最後", "出場日", "本規則", "原版", "差（點）"])) + "</tr></thead><tbody>")
    for r in J_.sort_values("t_in").to_dict("records"):
        evs = "<br>".join(f"{a} {dt(t)} {p:.2f}" for a, t, p in r["事件"]) or "—"
        H.append(f"<tr><td class='l'>{r['sid']}</td><td class='l'>{html.escape(r['名稱'])}</td><td data-v='{r['t_in']}'>{dt(r['t_in'])}</td><td>{r['進場價']:.2f}</td>"
                 f"<td class='l small'>{evs}</td><td class='l small'>{html.escape(r['結果'])}</td><td data-v='{r['出場t'] if r['出場t'] is not None else 99999}'>{dt(r['出場t'])}</td>"
                 f"<td class='{cls(r['規則淨'])}' data-v='{r['規則淨']}'>{P(r['規則淨'])}</td><td class='{cls(r['原版淨'])}' data-v='{r['原版淨']}'>{P(r['原版淨'])}</td>"
                 f"<td class='{cls(r['差'])}' data-v='{r['差']}'>{r['差'] * 100:+.2f}</td></tr>")
    H.append("</tbody></table></div>")
    H.append(f"<h3>乙 {py}（{len(Y_)} 筆）</h3><div class='wrap'><table><thead><tr>" + "".join(f"<th class='s{' l' if i_ in (0, 1, 8) else ''}' onclick='srt(this)'>{h}</th>" for i_, h in enumerate(
        ["代號", "名稱", "進場日", "進場價", "基準日", "起始基準", "最終基準", "上調次數", "出場原因", "出場日", "持有天數", "本規則", "原版", "差（點）"])) + "</tr></thead><tbody>")
    for r in Y_.sort_values("t_in").to_dict("records"):
        H.append(f"<tr><td class='l'>{r['sid']}</td><td class='l'>{html.escape(r['名稱'])}</td><td data-v='{r['t_in']}'>{dt(r['t_in'])}</td><td>{r['進場價']:.2f}</td>"
                 f"<td>{dt(r['基準日t']) if r['基準日t'] is not None and np.isfinite(r['基準日t']) else '—'}</td><td>{r['基準0']:.2f}</td><td>{r['最終基準']:.2f}</td><td>{int(r['上調'])}</td>"
                 f"<td class='l small'>{html.escape(r['結果'])}</td><td data-v='{r['出場t'] if r['出場t'] is not None else 99999}'>{dt(r['出場t'])}</td><td>{int(r['持有天數'])}</td>"
                 f"<td class='{cls(r['規則淨'])}' data-v='{r['規則淨']}'>{P(r['規則淨'])}</td><td class='{cls(r['原版淨'])}' data-v='{r['原版淨']}'>{P(r['原版淨'])}</td>"
                 f"<td class='{cls(r['差'])}' data-v='{r['差']}'>{r['差'] * 100:+.2f}</td></tr>")
    H.append("</tbody></table></div><p class='note'>「原版」＝同一筆訊號照營量 v1 抱 60 天（不論原版組合當時有沒有買到）。甲挑中格抱 40 天，沒觸發的筆也會和原版不同。</p>")
    # 6 例子
    H.append("<h2 id='s6'>6 K 線例子（按情況分類、每類 4 筆；點標題展開）</h2><p class='note'>每類 2 筆照規則（該類「差 ＝ 本規則 − 原版」最高、最低各 1）＋ 2 筆固定種子隨機抽。"
             "▲藍 進場｜▼灰 原版第 60 天出場｜▼紅 本規則賣出｜▲橘 買回｜▼黑 本規則最後出場｜橘虛線 基準（甲：成本×(1−b)；乙：起始與最終基準）</p>" + CS.legend_html())
    H.append("<div class='wrap'><table><tr><th class='l'>件｜類</th><th>筆數</th><th>占確認段</th><th>本規則平均</th><th>原版平均</th><th>差平均（點）</th></tr>")
    for fam, G_ in (("甲", J_), ("乙", Y_)):
        for cat, g in G_.groupby("類", sort=False):
            H.append(f"<tr><td class='l'>{fam}｜{cat}</td><td>{len(g)}</td><td>{len(g) / len(G_):.0%}</td><td>{P(g['規則淨'].mean())}</td><td>{P(g['原版淨'].mean())}</td><td>{g['差'].mean() * 100:+.2f}</td></tr>")
    H.append("</table></div>")
    last = None
    for fam, cat, i, how in PICK:
        G_ = J_ if fam == "甲" else Y_
        first = (fam, cat) != last
        if first:
            g = G_[G_["類"] == cat]
            H.append(f"<h3>{fam}｜{cat}：確認段 {len(g)} 筆、占 {len(g) / len(G_):.0%}（本規則平均 {P(g['規則淨'].mean())}、原版 {P(g['原版淨'].mean())}）</h3>")
            last = (fam, cat)
        name = f"{fam}｜{cat}"
        r = G_.loc[i]; s = r["sid"]; t_in = int(r["t_in"])
        df = D.load_stock(s, mk.get(s, "twse"), cal).df
        xo = min(int(r["x0"]), len(cal) - 1); t_out = min(int(r["出場t"]) if pd.notna(r["出場t"]) else len(cal) - 1, len(cal) - 1)
        i0 = max(0, t_in - 30); i1 = min(len(cal) - 1, max(xo, t_out) + 10); sl = slice(i0, i1 + 1)
        cf = pd.Series(df["close"].to_numpy(float)).ffill().to_numpy()
        ma = {k: CS.moving_avg(cf, k)[sl] for k in (5, 20, 60)}
        P0 = float(op_[s][t_in])
        marks = [{"i": t_in - i0, "px": P0, "kind": "entry", "label": f"進 {P0:.2f}"},
                 {"i": xo - i0, "px": float(cf[xo]), "kind": "exit", "label": f"原版出 {cf[xo]:.2f}", "color": "#888888", "row": 1}]
        hl = []
        if fam == "甲":
            for a_, t_, p_ in r["事件"]:
                marks.append({"i": t_ - i0, "px": p_, "kind": "exit" if a_ == "賣" else "entry", "label": f"{a_} {p_:.2f}", "color": "#c62828" if a_ == "賣" else "#ef6c00", "row": 0 if a_ == "賣" else 1})
            ab = r["放棄"] if isinstance(r["放棄"], str) else None          # ⚠ None 存進 DataFrame 會變 NaN（真值），⛔ 不可直接當布林
            if ab in ("警訊", "等滿10", "買回上限"):
                marks.append({"i": t_out - i0, "px": float(cf[t_out]), "kind": "exit", "label": f"放棄（{'10 天' if ab == '等滿10' else ab}）、換下一檔", "row": 2})
            elif bool(r["終於暫出"]):
                marks.append({"i": t_out - i0, "px": float(cf[t_out]), "kind": "exit", "label": f"第 {Hj} 天結束（仍在外）", "row": 2})
            else:
                marks.append({"i": t_out - i0, "px": float(cf[t_out]), "kind": "exit", "label": f"第 {Hj} 天出場 {cf[t_out]:.2f}"})
            hl.append({"px": P0 * (1 - bj), "label": f"成本×{1 - bj:.2f} ＝ {P0 * (1 - bj):.2f}", "color": "#e65100"})
            sub = f"暫出 {int(r['出'])} 次、買回 {int(r['買回'])} 次｜{r['結果']}"
        else:
            px_out = float(op_[s][t_out]) if r["結果"] == "跌破基準" else float(cf[t_out])
            marks.append({"i": t_out - i0, "px": px_out, "kind": "exit", "label": f"規則出 {px_out:.2f}"})
            if np.isfinite(r["基準0"]):
                hl.append({"px": float(r["基準0"]), "label": f"起始基準 {r['基準0']:.2f}", "color": "#e65100"})
                if r["最終基準"] > r["基準0"]:
                    hl.append({"px": float(r["最終基準"]), "label": f"最終基準 {r['最終基準']:.2f}（上調 {int(r['上調'])} 次）", "color": "#bf360c"})
            sub = f"持有 {int(r['持有天數'])} 天｜{r['結果']}"
        dates = [str(z.date()) for z in cal[sl]]
        svg = CS.kline_svg(dates, df["open"].to_numpy(float)[sl], df["high"].to_numpy(float)[sl], df["low"].to_numpy(float)[sl], df["close"].to_numpy(float)[sl],
                           df["volume"].to_numpy(float)[sl] / 1000.0, ma=ma, marks=marks, shade=(t_in - i0, t_out - i0), title=name, show_title=False, hlines=hl)
        H.append(f"<details class='card'{' open' if first else ''}><summary><b>{html.escape(s)} {html.escape(r['名稱'])}</b>｜進場 {dt(t_in)}｜原版 {P(r['原版淨'])} → 本規則 {P(r['規則淨'])}"
                 f"｜差 <b class='{cls(r['差'])}'>{r['差'] * 100:+.2f} 點</b></summary><div class='meta'>挑法：{html.escape(how)}｜{html.escape(sub)}</div>{svg}"
                 f"<div class='meta' style='font-size:.95rem;color:#222'>原版 <b>{P(r['原版淨'])}</b>｜本規則 <b>{P(r['規則淨'])}</b>｜差 <b class='{cls(r['差'])}'>{r['差'] * 100:+.2f} 點</b>（都扣成本）</div></details>")
    H.append(f"<p class='note'>資料：resultsYLexit3（fa41153bae）主世界、種子 0；查核（view/check.json）：{'全過' if CK['全過'] else '⛔ 有不過'}。</p></main></body></html>")
    open(os.path.join(OUT, F_HTML), "w", encoding="utf-8").write("\n".join(H))
    print(json.dumps(CK, ensure_ascii=False, indent=1))
    for fam, cat, i, how in PICK:
        G_ = J_ if fam == "甲" else Y_; r = G_.loc[i]
        print(fam, cat, how[:6], r["sid"], r["名稱"], dt(r["t_in"]), f"{r['原版淨']:+.4f} → {r['規則淨']:+.4f}（{r['差'] * 100:+.2f}）")
    print("甲筆", len(J_), "乙筆", len(Y_), "圖", len(PICK), os.path.getsize(os.path.join(OUT, F_HTML)))


if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
"""PREREG營量出場 seq1：例子網頁（使用者 09-28「請挑幾個例子給我看看」；⛔ 只描述、不改任何判定）。回測線，2026-09-28。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchYLexit_examples

範圍：確認段 2022-01-03～2026-08-24 進場、種子 0（營量 relvol 排序不抽籤）、各件挑中格（甲 b5_H40、乙 k60_C120）在自己組合裡【實際成交】的每一筆。
報酬（都扣成本）：
  本規則 ＝ 引擎 audit 該筆賣出金額 ÷ 買進金額 − 1 − 0.585%（甲的暫出再進成本已在合成路徑內）
  原版   ＝ 同一筆訊號照營量 v1（第 60 天收盤出）：AND 表 g_H60 − 0.585%（⚠ 不論原版組合當時有沒有買到這一筆；有買到的另對原版組合 audit）
挑法（⭐ 寫死、不看圖挑）：
  甲 ① 躲掉大跌 ＝ 所有暫出段中「暫出期間該股漲跌」（賣出開盤 → 買回開盤或結束收盤）最負的那一段所在那筆
     ② 來回被洗 ＝ 有買回的暫出段中，買回價 ＞ 賣出價、暫出根數最短；同長取進場日最早
     ③ 暫出後漲回 ＝ 有買回的暫出段中，買回價 ÷ 賣出價 − 1 最大（與 ① ② 同筆則取下一名）
     ④ 沒觸發 ＝ 沒觸發的筆中，報酬最接近這群中位數的那筆（取低中位）
  乙 ① 多抱賺最多 ＝ 本規則 − 原版 最大
     ② 很快跌破 ＝ 「第 60 天後跌破基準出場」的筆中持有根數最少；同長取 |差| 最小
     ③ 抱到上限 ＝ 觸頂 120 天的筆中，差的低中位
統計：甲 沒觸發／觸發後賺／觸發後虧（本規則扣成本後報酬的正負）；乙 多抱比原版好／差／相同（本規則 − 原版）
輸出 backtest/resultsYLexit/examples/營量出場例子_20260928.html、examples.csv、trades_seed0.csv.gz、check.json
"""
from __future__ import annotations

import hashlib
import html
import json
import os
import subprocess
import sys
import importlib.util

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import data as D
from backtest import rerun17 as RR
from backtest import research11 as R11
from backtest import researchYLexit as YX
from backtest import chart_svg as CS

OUT = "backtest/resultsYLexit/examples"
F_HTML = "營量出場例子_20260928.html"
COST = R11.COST
C0, C1 = "2022-01-03", "2026-08-24"
JIA = ("營量", "甲", (0.05, 40)); YI = ("營量", "乙", (60, 120)); BASE = ("營量", "base", None)


def sha(eq):
    return hashlib.sha256(np.asarray(eq, float).tobytes()).hexdigest()[:16]


def trades(aud):
    """audit ⇒ 每筆（買進 t、賣出 t、金額、淨報酬）。"""
    op = {}; rows = []
    for a in sorted(aud, key=lambda z: (z["t"], z["side"] != "sell")):
        if a["side"] == "buy":
            op[a["sid"]] = a
        else:
            b = op.pop(a["sid"])
            rows.append({"key": a["sid"], "t_in": b["t"], "t_out": a["t"], "buy": b["amt"], "sell": a["amt"], "cost": a["cost"],
                         "淨": a["amt"] / b["amt"] - 1 - a["cost"] / b["amt"], "ep": b["px"]})
    for k, b in op.items():
        rows.append({"key": k, "t_in": b["t"], "t_out": None, "buy": b["amt"], "sell": np.nan, "cost": np.nan, "淨": np.nan, "ep": b["px"]})
    return pd.DataFrame(rows)


def main():
    os.makedirs(OUT, exist_ok=True)
    # ── 世界（照 researchYLexit.main 主世界同一套）
    from backtest import researchT1fix as T1
    ctx = T1.build_ctx(True)
    cal = ctx["cal"]; mk = ctx["mk"]
    SF = R11.stop_force_days(R11.valid_from_data(sorted(ctx["closes"]), mk, cal), ctx["w1"])
    SEGP = {sg: (int(cal.searchsorted(pd.Timestamp(x))), int(cal.searchsorted(pd.Timestamp(y)))) for sg, (x, y) in YX.SEG_C.items()}
    W = {"cal": cal, "NP": ctx["ncal"], "closes": ctx["closes"], "opens": ctx["opens"], "SF": SF, "mk": mk, "w0": ctx["w0"], "w1": ctx["w1"], "SEGP": SEGP, "BARS": {}, "EVD": {}}
    W["SIGH"] = {("營量", 60): ctx["sig13"]}
    t40, _ = YX.exits_H(W, ctx["sig13"], 40); W["SIGH"][("營量", 40)] = t40[t40["xpos_H40"] >= 0]
    YX._W["主"] = W
    SE = pd.read_csv("backtest/resultsYLexit/seeds.csv.gz", dtype={"eq_sha": str}, low_memory=False)
    CK = {}; T = {}
    for cell in (BASE, JIA, YI):
        sig, rule, cl, op, sf, hm = YX.cell_inputs(W, cell)
        o, aud = YX._eng(W, "營量", sig, rule, 7000, closes=cl, opens=op, SF=sf, held_map=hm)
        ref = SE[(SE["世界"] == "主") & (SE["格"] == YX.cellname(cell)) & (SE["r"] == 0)]["eq_sha"].iloc[0]
        CK[f"種子0 權益 ＝ seeds.csv（{YX.cellname(cell)}）"] = sha(o["equity"]) == ref
        T[cell] = trades(aud)
    t0c = int(cal.searchsorted(pd.Timestamp(C0))); t1c = int(cal.searchsorted(pd.Timestamp(C1)))
    base = ctx["sig13"].reset_index(drop=True)
    orig = {(s, int(e)): (int(x), float(g)) for s, e, x, g in zip(base["sid"], base["entry_pos"], base["xpos_H60"], base["g_H60"])}
    bt = T[BASE].copy(); bt["sid"] = bt["key"]; borig = {(r.sid, int(r.t_in)): r.淨 for r in bt.itertuples()}
    # ── 甲
    jsig = YX.cell_inputs(W, JIA)[0]
    jst = {(st["sid"], int(st["e"])): st for st in W["JSTAT"][JIA]}
    jt = T[JIA]; jt = jt[(jt["t_in"] >= t0c) & (jt["t_in"] <= t1c)].copy()
    jt["sid"] = jt["key"].str.split("#").str[0]
    rows = []
    for r in jt.itertuples():
        st = jst[(r.sid, int(r.t_in))]; x0, g0 = orig[(r.sid, int(r.t_in))]
        xr = int(jsig.loc[(jsig["usid"] == r.sid) & (jsig["entry_pos"] == r.t_in), "xpos_H40"].iloc[0])
        gr = float(jsig.loc[(jsig["usid"] == r.sid) & (jsig["entry_pos"] == r.t_in), "g_H40"].iloc[0])
        rows.append({"sid": r.sid, "t_in": int(r.t_in), "t_out": r.t_out, "規則淨": r.淨, "規則淨_路徑": gr - COST if r.t_out == xr else np.nan,
                     "原版淨": g0 - COST, "原版xpos": x0, "原版組合有買": (r.sid, int(r.t_in)) in borig,
                     "出": st["出"], "進": st["進"], "終於暫出": st["終於暫出"], "段": st["暫出段"], "xr": xr})
    J = pd.DataFrame(rows); J["差"] = J["規則淨"] - J["原版淨"]
    J["類"] = np.where(J["出"] == 0, "沒觸發", np.where(J["規則淨"] > 0, "觸發後賺", "觸發後虧"))
    # 挑
    segs = [(i, s) for i, r in J.iterrows() for s in r["段"]]
    ex = {}
    i1 = min(segs, key=lambda z: z[1][2])[0]; ex["甲①暫出後躲掉大跌"] = i1
    reb = [(i, s) for i, s in segs if J.at[i, "進"] > 0 and any(s == z for z in J.at[i, "段"][:J.at[i, "進"]])]
    c2 = [(i, s) for i, s in reb if s[2] > 0]
    i2 = sorted(c2, key=lambda z: (z[1][1] - z[1][0], J.at[z[0], "t_in"]))[0][0]; ex["甲②來回被洗"] = i2
    c3 = sorted(c2, key=lambda z: -z[1][2]); i3 = next(i for i, _ in c3 if i not in (i1, i2)); ex["甲③暫出後漲回、買回比賣出貴"] = i3
    nt = J[J["出"] == 0].sort_values("原版淨"); i4 = nt.index[(len(nt) - 1) // 2]; ex["甲④沒觸發"] = i4
    # ── 乙
    ysig = YX.cell_inputs(W, YI)[0]; held, _ = W["YSTAT"][YI]
    ymap = {(s, int(e)): (int(x), float(g), float(h)) for s, e, x, g, h in zip(ysig["sid"], ysig["entry_pos"], ysig["xpos_H60"], ysig["g_H60"], held)}
    yt = T[YI]; yt = yt[(yt["t_in"] >= t0c) & (yt["t_in"] <= t1c)].copy(); yt["sid"] = yt["key"]
    rows = []
    for r in yt.itertuples():
        x0, g0 = orig[(r.sid, int(r.t_in))]; xr, gr, hd = ymap[(r.sid, int(r.t_in))]
        k = int(base.loc[(base["sid"] == r.sid) & (base["entry_pos"] == r.t_in), "k"].iloc[0])
        rows.append({"sid": r.sid, "t_in": int(r.t_in), "t_out": r.t_out, "規則淨": r.淨, "規則淨_路徑": gr - COST if r.t_out == xr else np.nan,
                     "原版淨": g0 - COST, "原版xpos": x0, "原版組合有買": (r.sid, int(r.t_in)) in borig, "持有根數": hd, "xr": xr, "k": k})
    Y = pd.DataFrame(rows); Y["差"] = Y["規則淨"] - Y["原版淨"]
    Y["類"] = np.where(Y["差"] > 0, "多抱比原版好", np.where(Y["差"] < 0, "多抱比原版差", "與原版相同"))
    ey = {}
    ey["乙①多抱賺最多"] = Y["差"].idxmax()
    br = Y[(Y["持有根數"] > 60) & (Y["持有根數"] < 120)].copy(); br["ad"] = br["差"].abs()
    ey["乙②60日後很快跌破"] = br.sort_values(["持有根數", "ad"]).index[0]
    cc = Y[Y["持有根數"] >= 120].sort_values("差"); ey["乙③抱到上限120天"] = cc.index[(len(cc) - 1) // 2]
    # ── 查核
    J_ok = J.dropna(subset=["規則淨_路徑"]); Y_ok = Y.dropna(subset=["規則淨_路徑"])
    CK["甲 規則淨（audit）＝ 合成路徑 g − 成本（排程出場的筆）"] = {"筆": int(len(J_ok)), "最大差": float((J_ok["規則淨"] - J_ok["規則淨_路徑"]).abs().max())}
    CK["乙 規則淨（audit）＝ 改寫後 g − 成本（排程出場的筆）"] = {"筆": int(len(Y_ok)), "最大差": float((Y_ok["規則淨"] - Y_ok["規則淨_路徑"]).abs().max())}
    bo = [(borig[(r.sid, r.t_in)], r.原版淨) for r in J.itertuples() if r.原版組合有買] + [(borig[(r.sid, r.t_in)], r.原版淨) for r in Y.itertuples() if r.原版組合有買]
    CK["原版淨（AND g_H60 − 成本）＝ 原版組合 audit（兩邊都有買的筆；差 ＞ 1e−12 的筆數，強制出場另計）"] = int(sum(abs(a - b) > 1e-12 for a, b in bo if np.isfinite(a)))
    head = subprocess.run(["git", "show", "HEAD:backtest/chart_svg.py"], capture_output=True, text=True).stdout
    hp = os.path.join(OUT, "_cs_head.py"); open(hp, "w", encoding="utf-8").write(head)
    spec = importlib.util.spec_from_file_location("backtest._cs_head", hp); Mh = importlib.util.module_from_spec(spec); spec.loader.exec_module(Mh); os.remove(hp)
    import shutil; shutil.rmtree(os.path.join(OUT, "__pycache__"), ignore_errors=True)
    rng = np.random.default_rng(1); n = 50; c_ = 10 + np.cumsum(rng.normal(0, 0.2, n)); o_ = c_ + rng.normal(0, 0.1, n)
    args = ([f"2026-01-{i:02d}" for i in range(n)], o_, np.maximum(o_, c_) + 0.2, np.minimum(o_, c_) - 0.2, c_, rng.uniform(1, 5, n))
    kw = dict(ma={5: CS.moving_avg(c_, 5)}, marks=[{"i": 3, "px": o_[3], "kind": "entry", "label": "進"}, {"i": 40, "px": c_[40], "kind": "exit", "label": "出"}], shade=(3, 40), title="t")
    CK["chart_svg 預設輸出 ＝ HEAD 版（逐字）"] = CS.kline_svg(*args, **kw) == Mh.kline_svg(*args, **kw)
    # ── 輸出表
    def rowtxt(name, r, fam):
        d = str(cal[int(r["t_in"])].date())
        return {"例子": name, "代號": r["sid"], "進場日": d, "原版淨": r["原版淨"], "規則淨": r["規則淨"], "差（點）": r["差"] * 100,
                **({"出": r["出"], "進": r["進"]} if fam == "甲" else {"持有根數": r["持有根數"]})}
    EX = [rowtxt(k, J.loc[i], "甲") for k, i in ex.items()] + [rowtxt(k, Y.loc[i], "乙") for k, i in ey.items()]
    pd.DataFrame(EX).to_csv(os.path.join(OUT, "examples.csv"), index=False, float_format="%.10g")
    pd.concat([J.drop(columns=["段"]).assign(件="甲 b5_H40"), Y.assign(件="乙 k60_C120")]).to_csv(os.path.join(OUT, "trades_seed0.csv.gz"), index=False, float_format="%.17g")
    stJ = J["類"].value_counts(); stY = Y["類"].value_counts()
    # ── 網頁
    uni = D.load_universe().set_index("stock_id")["name"] if "name" in D.load_universe().columns else {}
    CSS = open("backtest/list_yl13_hist.py", encoding="utf-8").read().split('CSS = """')[1].split('"""')[0]
    H = ['<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">',
         "<title>營量出場例子</title>", f"<style>{CSS}</style></head><body><main id='top'>",
         "<h1>營量 v1 出場兩件：例子</h1>",
         "<p class='lead'>確認段（2022～2026）實際成交的每一筆裡，照固定規則挑出 7 個例子；⛔ 只是描述，判定照原報告：兩件都不合格、對營量 v1 分不出。"
         f"甲件 {len(J)} 筆中 <b>{stJ.get('沒觸發', 0)}</b> 筆沒觸發、<b>{stJ.get('觸發後賺', 0)}</b> 筆觸發後賺、<b>{stJ.get('觸發後虧', 0)}</b> 筆觸發後虧；"
         f"乙件 {len(Y)} 筆中 <b>{stY.get('多抱比原版好', 0)}</b> 筆多抱比原版好、<b>{stY.get('多抱比原版差', 0)}</b> 筆比原版差。</p>",
         "<h2>各類情況占幾成</h2><div class='wrap'><table><tr><th>件｜情況</th><th>筆數</th><th>占比</th><th>本規則平均</th><th>原版平均</th><th>差平均</th></tr>"]
    for fam, G_ in (("甲 跌破成本暫出（b5%、40 天）", J), ("乙 續抱確認（第 60 天基準、上限 120 天）", Y)):
        for k, g in G_.groupby("類"):
            H.append(f"<tr><td>{fam}｜{k}</td><td>{len(g)}</td><td>{len(g) / len(G_):.0%}</td><td>{g['規則淨'].mean() * 100:+.2f}%</td>"
                     f"<td>{g['原版淨'].mean() * 100:+.2f}%</td><td>{g['差'].mean() * 100:+.2f} 點</td></tr>")
        H.append(f"<tr><th>{fam}｜全部</th><th>{len(G_)}</th><th>100%</th><th>{G_['規則淨'].mean() * 100:+.2f}%</th><th>{G_['原版淨'].mean() * 100:+.2f}%</th>"
                 f"<th>{G_['差'].mean() * 100:+.2f} 點</th></tr>")
    H.append("</table></div><p class='note'>報酬都扣 0.585%（甲的每一趟暫出再進另扣一趟）。「原版」＝同一筆訊號照營量 v1 抱 60 天收盤出（不論原版組合當時有沒有買到）。"
             "還原價、種子 0（營量依 relvol 排序、不抽籤）。例子的挑法寫在每張圖上方，⛔ 沒有挑最漂亮的。</p>")
    H.append("<p class='note'>⚠ 甲件挑中格是「抱 40 天」，所以就算沒觸發，也會和原版（抱 60 天）不一樣；差距同時包含「暫出再進」與「早 20 天結束」兩件事。"
             "乙件有 17 筆與原版完全相同（大多是進場太晚、第 60 天已超過資料末日，照原版處理）。</p>")
    H.append("<p class='note'>圖例：▲藍＝進場｜▼灰＝原版第 60 天出場｜▼紅＝本規則賣出｜▲橘＝本規則買回｜▼黑＝本規則最後出場｜橘虛線＝基準線（甲：成本×0.95；乙：第 60 天收盤）</p>")
    H.append(CS.legend_html())
    RULE = {"甲①暫出後躲掉大跌": "挑法：所有暫出段中，暫出期間該股跌最多的那一段",
            "甲②來回被洗": "挑法：有買回、且買回價高於賣出價的暫出段中，暫出天數最短的",
            "甲③暫出後漲回、買回比賣出貴": "挑法：有買回的暫出段中，買回價比賣出價高最多的（與前兩例不同筆）",
            "甲④沒觸發": "挑法：沒觸發的筆中，報酬最接近中位數的",
            "乙①多抱賺最多": "挑法：本規則比原版多賺最多的",
            "乙②60日後很快跌破": "挑法：第 60 天後跌破基準出場的筆中，持有天數最少的",
            "乙③抱到上限120天": "挑法：抱到上限 120 天的筆中，差距的中位數那筆"}
    ne = 0
    for fam, sel, G_ in (("甲", ex, J), ("乙", ey, Y)):
        for name, i in sel.items():
            r = G_.loc[i]; s = r["sid"]; t_in = int(r["t_in"])
            st = D.load_stock(s, mk.get(s, "twse"), cal); df = st.df
            x0 = int(r["原版xpos"]); xo = min(x0, len(cal) - 1)
            t_out = int(r["t_out"]) if pd.notna(r["t_out"]) else len(cal) - 1; t_out = min(t_out, len(cal) - 1)
            i0 = max(0, t_in - 30); i1 = min(len(cal) - 1, max(xo, t_out) + 10)
            sl = slice(i0, i1 + 1); cf = pd.Series(df["close"].to_numpy(float)).ffill().to_numpy()
            ma = {k: CS.moving_avg(cf, k)[sl] for k in (5, 20, 60)}
            P0 = float(ctx["opens"][s][t_in])
            marks = [{"i": t_in - i0, "px": P0, "kind": "entry", "label": f"進 {P0:.2f}"},
                     {"i": xo - i0, "px": float(cf[xo]), "kind": "exit", "label": f"原版出 {cf[xo]:.2f}", "color": "#888888", "row": 1}]
            hl = []
            if fam == "甲":
                idx = W["BARS"][s][0]
                for sb, rb, _ in r["段"]:
                    ts = int(idx[sb]); marks.append({"i": ts - i0, "px": float(ctx["opens"][s][ts]), "kind": "exit", "label": f"賣 {ctx['opens'][s][ts]:.2f}", "color": "#c62828"})
                    if rb < len(idx) and int(idx[rb]) <= r["xr"]:
                        tb = int(idx[rb]); marks.append({"i": tb - i0, "px": float(ctx["opens"][s][tb]), "kind": "entry", "label": f"買回 {ctx['opens'][s][tb]:.2f}", "color": "#ef6c00", "row": 1})
                if not r["終於暫出"]:
                    marks.append({"i": t_out - i0, "px": float(cf[t_out]), "kind": "exit", "label": f"規則出 {cf[t_out]:.2f}"})
                hl.append({"px": P0 * 0.95, "label": f"成本×0.95 ＝ {P0 * 0.95:.2f}", "color": "#e65100"})
                shade = (t_in - i0, min(int(r["xr"]), len(cal) - 1) - i0)
                sub = f"暫出 {int(r['出'])} 次、買回 {int(r['進'])} 次" + ("（結束時仍在外）" if r["終於暫出"] else "")
            else:
                idx = W["BARS"][s][0]; kb = int(r["k"]) + 1 + 60 - 1; tk = int(idx[kb]) if kb < len(idx) else None
                px_out = float(ctx["opens"][s][t_out]) if (r["xr"] == t_out and np.isfinite(ctx["opens"][s][t_out]) and abs(r["規則淨"] + COST - (ctx["opens"][s][t_out] / P0 - 1)) < 1e-9) else float(cf[t_out])
                marks.append({"i": t_out - i0, "px": px_out, "kind": "exit", "label": f"規則出 {px_out:.2f}"})
                if tk is not None:
                    hl.append({"px": float(cf[tk]), "label": f"第 60 天收盤基準 ＝ {cf[tk]:.2f}", "color": "#e65100"})
                shade = (t_in - i0, t_out - i0)
                sub = f"持有 {int(r['持有根數'])} 天"
            dates = [str(x.date()) for x in cal[sl]]
            svg = CS.kline_svg(dates, df["open"].to_numpy(float)[sl], df["high"].to_numpy(float)[sl], df["low"].to_numpy(float)[sl], df["close"].to_numpy(float)[sl],
                               df["volume"].to_numpy(float)[sl] / 1000.0, ma=ma, marks=marks, shade=shade, title=name, show_title=False, hlines=hl)
            nm = str(uni.get(s, "")) if hasattr(uni, "get") else ""
            ne += 1
            H.append(f"<section class='card'><h3>{html.escape(name)}｜{s} {html.escape(nm)}｜進場 {cal[t_in].date()}</h3>"
                     f"<div class='meta'>{html.escape(RULE[name])}｜{html.escape(sub)}</div>{svg}"
                     f"<div class='meta' style='font-size:.95rem;color:#222'>原版 <b>{r['原版淨'] * 100:+.2f}%</b>｜本規則 <b>{r['規則淨'] * 100:+.2f}%</b>｜"
                     f"差 <b class='{'pos' if r['差'] > 0 else 'neg'}'>{r['差'] * 100:+.2f} 點</b>（都扣成本）</div></section>")
    H.append("<p class='note'>資料：resultsYLexit（researchYLexit.py）主世界、種子 0；查核見 examples/check.json。</p></main></body></html>")
    open(os.path.join(OUT, F_HTML), "w", encoding="utf-8").write("\n".join(H))
    json.dump(CK, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    print(json.dumps(CK, ensure_ascii=False, indent=1, default=str))
    print(pd.DataFrame(EX).to_string())
    print({k: v for k, v in stJ.items()}, {k: v for k, v in stY.items()}, len(J), len(Y))


if __name__ == "__main__":
    main()

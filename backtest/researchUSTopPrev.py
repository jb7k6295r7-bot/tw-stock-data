# -*- coding: utf-8 -*-
"""美股參考組「每年買去年 S&P 500 漲最多那檔」（IG gurgavin 轉述）——裁定 seq346 §一、seq349；規則照美股策略線 1014-0003 逐字。
性質：描述、⛔ 不計 N、⛔ 不判（2016 年後 IG 原文已公開 ⇒ 只能當對帳與描述）。早年段（2000～2015）資料到位後照 seq346 補算，本檔不做。

    cd ~/tw-p17 && PYTHONPATH=$HOME/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchUSTopPrev
    獨立查核：... -m backtest.researchUSTopPrev_check

重用（⛔ 不另寫資料載入）：researchUSC.rworld（C 批同一份世界 ~/us_work/a4/world.npz，us-stock-data 881c86a，聯集轉接層；point-in-time 成分 m5、
含下市、收盤 ＝ 轉接層還原價（總報酬口徑）、斷點 pb、最後有效 K 棒 last）、researchUSC.period_ret（錨點 5 根、⛔ 跨斷點）、researchUSC.metrics、
researchUSA4.bench_series（^SP500TR）、researchUSA1_data.fred("DTB3")（國庫券，~/usdata/60d2f99）、researchUSA1_data.dd_info（回本）。

═══ 本件讀法（T 標；寫死於 2026-10-14（台北），寫死前 ⛔ 沒看本件任何報酬）═══
 T1 窗：世界日曆 2015-11-02 起、K 棒 2015-12-01 起、S&P 500 成分旗標 2016-01-04 起（2015-12-31 無成分、無 2015 全年報酬）
    ⇒ 第一年 2016 選不出（用 2015 全年報酬）⇒ 第一年從 2017 起（照 0003 §二）。窗 ＝ [2016-12-30 收盤, 資料尾]；
    資料尾 ＝ 世界最後一個有個股 K 棒的交易日（2026-10-05；10-06 列無 K 棒）。^SP500TR 同窗。
 T2 選股：持有年 Y 的換股日 e_Y ＝ Y 年第一個交易日；排名日 s ＝ e_Y − 1（Y−1 年最後交易日）；基準日 b0 ＝ Y−2 年最後交易日。
    母體 ＝ m5[s]（point-in-time S&P 500）；全年總報酬 ＝ period_ret(b0, s)（還原收盤；b0 前 5 根內要有有效 K 棒、(b0, s] 不跨斷點，否則無全年報酬、不排）。
    依報酬遞減，同分依代號序。第 1 名 ＝ 單檔組；第 1～3 名 ＝ 三檔組。
    揭露：(a) 不排的成分股中，「上市以來（第一根有效 K 棒收盤→s）」或「跨斷點直接比」會進前 3 者列出（不改主臂）；
          (b) 對帳附表 V-IPO（描述、⛔ 不當主臂）：上市不滿一年者改用上市以來報酬一起排，看選股是否變。
 T3 交易：e_Y 開盤先賣舊持股（開盤價）、再以賣後全部資金依權重買（單檔 100%；三檔各 1/3，年中不再平衡）；同一檔連兩年入選也照賣出再買。
    成本 0.05% 來回 ＝ 賣出時扣「該筆進場金額 × 0.05%」（K3 同式）。窗尾（資料尾）仍持有 ⇒ 尾日收盤計值、⛔ 不扣賣出成本（K 同）。
 T4 下市、斷點、踢出指數（現行口徑 ＝ researchUSC K3／A4 G11、G12）：持股遇斷點 ⇒ 以前一日收盤結清；最後有效 K 棒之後 ⇒ 以最後收盤結清；
    被踢出指數但仍有 K 棒 ⇒ 照抱到下一個換股日（換股簿：落選於下一個換股日處理）。結清所得 ⇒ 現金（同 T5 計息）。各年事件逐筆報。
 T5 35% 停損（只第 1 名一格）：持有中某日有效收盤 ≤ 買價 × 0.65 ⇒ 次一個有效開盤賣（扣成本）、持現金到下一個換股日。
    現金報酬 ＝ DTB3（FRED 3 個月國庫券，%）：t 日 × (1 ＋ DTB3_{t−1}/100/252)（A1 D4 同式；FRED 缺值用前值）；換股日當天不計；0% 版另報。
    附註：「35% 是原文 10%～50% 九組中事後挑出」。
 T6 年報酬 ＝ 換股日開盤（買前資金）→ 下一換股日開盤（賣後資金）；2026 ＝ 2026-01-02 開盤 → 資料尾收盤。全窗權益 ＝ 逐年連乘（窗首 1.0）。
    ^SP500TR 逐年 ＝ 曆年收盤→收盤（2026 ＝ 2025-12-31 → 資料尾）。
 T7 全窗：年化（252 日）、最大回落、回本年數（dd_info：最大回落的高點→回到高點的交易日數 ÷ 252；未回本照寫）、年化÷|回落|。
    拿掉最好一年：該年報酬改 0（其餘年連乘）、窗長同（年化用同窗年數）、回落用拿掉後的逐日路徑（該年權益持平）。
    2026 貢獻占比 ＝ (權益_尾 − 權益_2025 末) ÷ (權益_尾 − 1)；單一持股貢獻 ＝ 2026 年單檔組只持一檔 ⇒ 同值；三檔組另報每檔。
 T8 對 IG 原文（gurgavin，X 2026-10-11 串文；threadreaderapp 轉錄）：逐年代號表只在圖片（無法取得文字）⇒ 只對串文文字提到的年份
    （2019 AMD ＋148%、2024 NVDA ＋171%、2025 PLTR ＋135%、2026 SNDK ＋566%〔至發文日〕）；其餘年寫「無法取得」，⛔ 不編。
 T9 私有資料：resultsUSC/topprev/ 只放彙總與代號；逐日權益寫 ~/us_work/topprev/（repo 外）並列 sha。
 T10 存活者偏差（必寫，同 K10）：S&P 500 有 18 檔不在母體 ⇒ 偏向存活股、偏樂觀。
"""
from __future__ import annotations

import csv
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17"))
from backtest import researchUSC as K          # noqa: E402

RULING = "裁定 seq346 §一（2026-10-13 23:49）、seq349（2026-10-14 00:05）；規則 ＝ 美股策略線 1014-0003 逐字"
OUTD = os.path.join(K.OUT, "topprev")
WORKD = os.path.expanduser("~/us_work/topprev")
COST = K.COST
STOP = 0.35
Y0 = 2017
NOTE_STOP = "35% 停損為原文 10%～50% 九組中事後挑出"
NOTE_N = "參考組：描述、不計 N、不判；2016 年後 IG 原文已公開 ⇒ 只能當對帳與描述"
IG = {2019: ("AMD", 1.48), 2024: ("NVDA", 1.71), 2025: ("PLTR", 1.35), 2026: ("SNDK", 5.66)}
IG_SRC = ("gurgavin X 串文（2026-10-11；https://x.com/gurgavin/status/2109399629431488571，"
          "轉錄 https://threadreaderapp.com/thread/2109399629431488571.html）；逐年表在圖片 3/、無文字 ⇒ 只對文字提到的年份；"
          "1997 起 $100 → $89,418、加 35% 停損 → $1,514,581（30 年版）")


def world():
    R = K.rworld(); W = R["Wd"]; cal = R["cal"]
    nv = W["valid"].sum(axis=1)
    tail = int(np.flatnonzero(nv > 0)[-1])
    years = sorted(set(cal.year))
    e = {}
    for y in years:
        ix = np.flatnonzero(cal.year == y)
        if len(ix):
            e[y] = int(ix[0])
    return R, W, cal, tail, e


def dtb3_daily(cal):
    from backtest import researchUSA1_data as A1
    d = A1.fred("DTB3"); d.index = pd.to_datetime(d.index)
    s = d.ffill().reindex(cal.union(d.index)).ffill().reindex(cal).to_numpy(float)
    g = np.zeros(len(cal)); g[1:] = s[:-1] / 100 / 252          # t 日現金報酬 ＝ DTB3_{t−1}/100/252
    return np.nan_to_num(g), {"來源": "researchUSA1_data.fred('DTB3')（%s）" % A1.ROOT, "最後一筆": str(d.dropna().index[-1].date())}


def rank_year(R, W, cal, e, y):
    s = e[y] - 1; b0 = e[y - 1] - 1
    assert cal[s].year == y - 1 and cal[b0].year == y - 2
    r = K.period_ret(b0, s)
    mem = W["m5"][s]
    el = np.flatnonzero(mem & np.isfinite(r))
    order = el[np.lexsort((el, -r[el]))]
    # 揭露（T2 a）：不排的成分股
    fv = W["first"]; V = W["valid"]
    aok = K.anchor_ok(b0)
    third = r[order[2]] if len(order) >= 3 else -np.inf
    noRank = np.flatnonzero(mem & ~np.isfinite(r))
    disc = []; alt = {}
    for j in noRank:
        crosses = bool(W["pb"][b0 + 1:s + 1, j].any())
        if crosses and aok[j]:
            why = "跨斷點"; f0 = b0
        else:
            ff = np.flatnonzero(V[b0 + 1:s + 1, j])                    # 年內第一根有效 K 棒
            f0 = (b0 + 1 + int(ff[0])) if len(ff) else None
            why = "上市不滿一年" if fv[j] > b0 - 4 else "基準日附近無有效K棒（年內資料缺口）"
        if f0 is None:
            continue
        with np.errstate(invalid="ignore", divide="ignore"):
            v = W["CF"][s, j] / W["CF"][f0, j] - 1
        alt[j] = (v, f0)
        if np.isfinite(v) and v > third:
            disc.append({"代號": str(W["tick"][j]), "原因": why, "替代報酬（起點→排名日）": float(v), "替代起點": str(cal[f0].date()),
                         "第一根K棒": str(cal[fv[j]].date()) if fv[j] < len(cal) else None})
    # V-IPO（T2 b）：上市不滿一年者用上市以來報酬一起排（上市以來不跨斷點者）
    rv = r.copy()
    for j in noRank:
        if j in alt and fv[j] > b0 - 4 and alt[j][1] == fv[j] and not W["pb"][fv[j] + 1:s + 1, j].any():
            rv[j] = alt[j][0]
    elv = np.flatnonzero(mem & np.isfinite(rv))
    ordv = elv[np.lexsort((elv, -rv[elv]))]
    return {"s": s, "b0": b0, "order": [int(x) for x in order], "r": r, "排名檔數": int(len(el)), "成分檔數": int(mem.sum()),
            "未排": int(len(noRank)), "揭露": disc, "order_v": [int(x) for x in ordv], "V-IPO前3": [(str(W["tick"][j]), float(rv[j])) for j in ordv[:3]]}


def run(W, cal, e, tail, picks, weights, stop=None, cash_g=None):
    """picks：{y: [j…]}；weights：{y: [w…]}。逐日引擎 ⇒ eq（窗首 e_Y0−1 ＝ 1.0）、逐年報酬、事件。"""
    O, C, CF, valid, last, pb = W["O"], W["C"], W["CF"], W["valid"], W["last"], W["pb"]
    n = len(cal); ys = sorted(picks)
    a = e[ys[0]] - 1
    eq = np.full(n, np.nan); eq[a] = 1.0
    cash = 1.0; pos = {}            # j → [股數, 進場金額, 買價, 進場日]
    pend = set(); ev = []; yr = {}; yst = {}; start_val = None; cur_y = None
    rebs = {e[y]: y for y in ys}
    g = np.zeros(n) if cash_g is None else cash_g
    for t in range(a + 1, tail + 1):
        isreb = t in rebs
        if not isreb:
            cash *= 1 + g[t]
        # 斷點／下市結清（T4）
        for j in list(pos):
            u, amt, bp, b = pos[j]
            if t > b and pb[t, j]:
                px = CF[t - 1, j]; why = "斷點"
            elif t > last[j]:
                px = CF[last[j], j]; why = "下市"
            else:
                continue
            pos.pop(j); pend.discard(j); cash += u * px - amt * COST
            ev.append({"年": cur_y, "代號": str(W["tick"][j]), "事件": why, "日": str(cal[t].date())})
        if isreb:
            for j in list(pos):
                u, amt, bp, b = pos.pop(j)
                assert valid[t, j] and np.isfinite(O[t, j]) and O[t, j] > 0, ("換股日開盤無效", W["tick"][j], cal[t])
                cash += u * O[t, j] - amt * COST
            pend.clear()
            if cur_y is not None:
                yr[cur_y] = cash / start_val
            cur_y = rebs[t]; start_val = cash; yst[cur_y] = cash
            tot = cash
            for j, w in zip(picks[cur_y], weights[cur_y]):
                o = O[t, j]
                assert valid[t, j] and np.isfinite(o) and o > 0, ("買進開盤無效", W["tick"][j], cal[t])
                amt = tot * w; cash -= amt; pos[j] = [amt / o, amt, o, t]
            if abs(cash) < 1e-15:
                cash = 0.0
        else:
            for j in sorted(pend):
                if j in pos and valid[t, j] and np.isfinite(O[t, j]) and O[t, j] > 0:
                    u, amt, bp, b = pos.pop(j); cash += u * O[t, j] - amt * COST; pend.discard(j)
                    ev.append({"年": cur_y, "代號": str(W["tick"][j]), "事件": "停損賣出", "日": str(cal[t].date()),
                               "賣價÷買價−1": float(O[t, j] / bp - 1)})
        eq[t] = cash + sum(p[0] * CF[t, j] for j, p in pos.items())
        if stop is not None:
            for j, p in pos.items():
                if j not in pend and valid[t, j] and C[t, j] <= p[2] * (1 - stop):
                    pend.add(j)
                    ev.append({"年": cur_y, "代號": str(W["tick"][j]), "事件": "停損觸發（收盤）", "日": str(cal[t].date()),
                               "收盤÷買價−1": float(C[t, j] / p[2] - 1)})
    yr[cur_y] = eq[tail] / start_val
    return eq, {y: v - 1 for y, v in yr.items()}, ev, [str(W["tick"][j]) for j in pos], yst


def summarize(eq, a, tail, cal):
    """T7：年化、回落、比值（K.metrics）；回本年數 ＝ 最大回落的高點日 → 第一次收盤權益 ≥ 高點 的交易日數 ÷ 252。"""
    m = K.metrics(eq, a, tail)
    seg = np.asarray(eq[a:tail + 1], float)
    pk = np.maximum.accumulate(seg); dd = (seg - pk) / pk
    it = int(np.argmin(dd)); ip = int(np.argmax(seg[:it + 1]))
    back = np.flatnonzero(seg[it:] >= seg[ip])
    m.update({"高點日": str(cal[a + ip].date()), "谷底日": str(cal[a + it].date()),
              "回本年數": ((it + int(back[0]) - ip) / 252) if len(back) else "段內未回本（至資料尾）",
              "回本日": str(cal[a + it + int(back[0])].date()) if len(back) else None,
              "期末倍數": float(seg[-1] / seg[0])})
    return m


def drop_best_bench(eq, yr, e, a, tail, cal):
    """T7（基準）：最好一曆年報酬改 0（該年權益持平、之後整段除以 1＋r）。"""
    yb = max(yr, key=lambda y: yr[y])
    t0 = e[yb]; t1 = (e[yb + 1] - 1) if (yb + 1) in e and e[yb + 1] <= tail else tail
    eq2 = eq.copy(); eq2[t0:t1 + 1] = eq[t0 - 1]
    if t1 < tail:
        eq2[t1 + 1:tail + 1] = eq[t1 + 1:tail + 1] / (1 + yr[yb])
    m = summarize(eq2, a, tail, cal); m["拿掉的年"] = int(yb); m["該年報酬"] = float(yr[yb])
    return m


def drop_best_arm(W, cal, e, tail, picks, weights, yr, stop, g, a, yb=None):
    """T7（策略）：最好一年（或指定 yb）改持現金 0%（該年不買、不計息）重跑；其餘年照原名單。"""
    yb = max(yr, key=lambda y: yr[y]) if yb is None else yb
    p2 = dict(picks); w2 = dict(weights); p2[yb] = []; w2[yb] = []
    g2 = None if g is None else g.copy()
    if g2 is not None:
        t1 = e[yb + 1] if (yb + 1) in e and e[yb + 1] <= tail else tail + 1
        g2[e[yb]:t1] = 0.0
    eq2, yr2, _, _, _ = run(W, cal, e, tail, p2, w2, stop=stop, cash_g=g2)
    assert abs(yr2[yb]) < 1e-15
    m = summarize(eq2, a, tail, cal); m["拿掉的年"] = int(yb); m["該年報酬"] = float(yr[yb])
    return m


def depth(W, e, tail, picks, y):
    """單檔組該年：最深收盤 ÷ 買價 − 1（有效收盤；買日～下一換股日前一日）。"""
    j = picks[y][0]; t0 = e[y]; t1 = (e[y + 1] - 1) if (y + 1) in e and e[y + 1] <= tail else tail
    c = W["C"][t0:t1 + 1, j]; c = c[np.isfinite(c)]
    return float(c.min() / W["O"][t0, j] - 1)


def main():
    os.makedirs(OUTD, exist_ok=True); os.makedirs(WORKD, exist_ok=True)
    R, W, cal, tail, e = world()
    years = [y for y in sorted(e) if y >= Y0 and e[y] <= tail]
    a = e[Y0] - 1
    g, gsrc = dtb3_daily(cal)
    rk = {y: rank_year(R, W, cal, e, y) for y in years}
    P1 = {y: rk[y]["order"][:1] for y in years}; W1 = {y: [1.0] for y in years}
    P3 = {y: rk[y]["order"][:3] for y in years}; W3 = {y: [1 / 3] * 3 for y in years}
    PV = {y: rk[y]["order_v"][:1] for y in years}
    spec = {"第1名": (P1, W1, None, g), "前3名等權": (P3, W3, None, g), "第1名＋35%停損": (P1, W1, STOP, g),
            "第1名＋35%停損（現金0%）": (P1, W1, STOP, None),
            "對帳V-IPO第1名（描述）": (PV, W1, None, g), "對帳V-IPO第1名＋35%停損（描述）": (PV, W1, STOP, g)}
    arms = {k: run(W, cal, e, tail, v[0], v[1], stop=v[2], cash_g=v[3]) for k, v in spec.items()}
    B = R["B"]
    beq = np.full(len(cal), np.nan); beq[a:tail + 1] = B[a:tail + 1] / B[a]
    byr = {}
    for y in years:
        t1 = (e[y + 1] - 1) if (y + 1) in e and e[y + 1] <= tail else tail
        byr[y] = float(B[t1] / B[e[y] - 1] - 1)

    tk = W["tick"]
    rows = []
    for y in years:
        r = rk[y]; o = r["order"]
        t1 = (e[y + 1] - 1) if (y + 1) in e and e[y + 1] <= tail else tail
        j1 = o[0]
        row = {"持有年": y, "排名日": str(cal[r["s"]].date()), "成分檔數": r["成分檔數"], "可排檔數": r["排名檔數"],
               "第1名": str(tk[o[0]]), "第1名前一年漲幅": float(r["r"][o[0]]),
               "第2名": str(tk[o[1]]), "第2名前一年漲幅": float(r["r"][o[1]]),
               "第3名": str(tk[o[2]]), "第3名前一年漲幅": float(r["r"][o[2]]),
               "當年_第1名": arms["第1名"][1][y], "當年_前3名等權": arms["前3名等權"][1][y],
               "當年_第1名＋35%停損": arms["第1名＋35%停損"][1][y], "當年_^SP500TR": byr[y],
               "第1名年內最深（收盤÷買價−1）": depth(W, e, tail, P1, y),
               "第1名曆年報酬（收盤→收盤，對帳用）": float(W["CF"][t1, j1] / W["CF"][e[y] - 1, j1] - 1),
               "持有區間": "%s 開盤 → %s" % (cal[e[y]].date(), ("%s 開盤" % cal[e[y + 1]].date()) if (y + 1) in e and e[y + 1] <= tail
                                             else "%s 收盤（資料尾）" % cal[tail].date())}
        if y in IG:
            ig = IG[y]
            row["IG原文"] = "%s ＋%.0f%%" % (ig[0], ig[1] * 100)
            row["IG對帳"] = ("代號一致" if ig[0] == row["第1名"] else "代號不一致")
        else:
            row["IG原文"] = "無法取得（原文逐年表只在圖片）"; row["IG對帳"] = "—"
        row["V-IPO第1名（對帳描述）"] = str(tk[PV[y][0]])
        row["V-IPO當年（對帳描述）"] = arms["對帳V-IPO第1名（描述）"][1][y]
        jv = PV[y][0]
        row["V-IPO第1名曆年報酬（收盤→收盤）"] = float(W["CF"][t1, jv] / W["CF"][e[y] - 1, jv] - 1)
        rows.append(row)

    full = {}
    for k, (eqk, yrk, ev, opn, yst) in arms.items():
        s = summarize(eqk, a, tail, cal)
        sp = spec[k]
        db = drop_best_arm(W, cal, e, tail, sp[0], sp[1], yrk, sp[2], sp[3], a)
        tot = eqk[tail] - 1; pre = yst.get(2026, np.nan)
        d26 = drop_best_arm(W, cal, e, tail, sp[0], sp[1], yrk, sp[2], sp[3], a, yb=2026)
        s.update({"拿掉最好一年": db, "拿掉2026（描述）": d26, "2026貢獻占比（占全窗總獲利）": float((eqk[tail] - pre) / tot) if tot > 0 else None,
                  "2026年初開盤權益": float(pre), "逐年報酬": {y: float(v) for y, v in yrk.items()}, "事件": ev, "窗尾仍持有": opn})
        full[k] = s
    bm = summarize(beq, a, tail, cal); bm["拿掉最好一年"] = drop_best_bench(beq, byr, e, a, tail, cal); bm["逐年報酬"] = byr
    full["^SP500TR"] = bm
    y = 2026
    if y in years:
        t0 = e[y]
        full["前3名等權"]["2026每檔（開盤→資料尾）"] = {str(tk[j]): float(W["CF"][tail, j] / W["O"][t0, j] - 1) for j in P3[y]}
        for k in arms:
            eqk, yrk, _, _, yst = arms[k]; tot = eqk[tail] - 1
            pk = spec[k][0][y]; wk = spec[k][1][y]
            full[k]["2026單一持股貢獻占比"] = {str(tk[j]): float(yst[y] * w * (W["CF"][tail, j] / W["O"][t0, j] - 1) / tot) for j, w in zip(pk, wk)}
    for k, s in full.items():
        if k == "^SP500TR":
            continue
        s["對基準"] = {"年化差": s["年化"] - bm["年化"], "比值": s["比值"], "基準比值": bm["比值"]}
        s["拿掉最好一年"]["對基準"] = {"年化差": s["拿掉最好一年"]["年化"] - bm["年化"], "比值": s["拿掉最好一年"]["比值"], "基準比值": bm["比值"]}

    # 逐日權益（repo 外）
    dpath = os.path.join(WORKD, "equity_daily.csv")
    pd.DataFrame({k: v[0][a:tail + 1] for k, v in arms.items()} | {"^SP500TR": beq[a:tail + 1]},
                 index=cal[a:tail + 1]).to_csv(dpath)
    out = {"件": "美股參考組：每年買去年 S&P 500 漲最多那檔", "依據": RULING, "性質": NOTE_N, "附註": [NOTE_STOP, K.SURV],
           "資料": {"世界": "~/us_work/a4/world.npz（us-stock-data 881c86a；researchUSC.rworld）", "現金": gsrc,
                   "窗": [str(cal[a].date()), str(cal[tail].date())], "資料尾": str(cal[tail].date()),
                   "第一年": "%d（2015-12-31 無 S&P 500 成分旗標、無 2015 全年報酬 ⇒ 2016 選不出）" % Y0},
           "成本": COST, "逐年": rows, "全窗": full,
           "排名揭露（不排但會進前3）": {y: rk[y]["揭露"] for y in years},
           "對帳附表V-IPO（上市不滿一年用上市以來報酬，描述）": {y: rk[y]["V-IPO前3"] for y in years},
           "IG原文": IG_SRC, "逐日權益（repo外）": {"path": dpath, "sha256": K.sha256f(dpath)}, "產出時間": K.now_tpe()}
    K.jdump(out, os.path.join(OUTD, "topprev.json"))
    with open(os.path.join(OUTD, "topprev_years.csv"), "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()) + [k for k in rows[-1] if k not in rows[0]])
        w.writeheader(); [w.writerow(r) for r in rows]
    # 螢幕摘要
    for r in rows:
        print("%d %-5s %+8.1f%% | %-5s %-5s | 1:%+7.1f%% 3:%+7.1f%% S:%+7.1f%% B:%+6.1f%% | %s" % (
            r["持有年"], r["第1名"], r["第1名前一年漲幅"] * 100, r["第2名"], r["第3名"], r["當年_第1名"] * 100, r["當年_前3名等權"] * 100,
            r["當年_第1名＋35%停損"] * 100, r["當年_^SP500TR"] * 100, r["IG對帳"]))
    for k, s in full.items():
        db = s["拿掉最好一年"]
        print("%-22s 年化 %+.2f%% 回落 %.2f%% 比值 %.3f 回本 %s 倍數 %.3f | 拿掉%d：年化 %+.2f%% 回落 %.2f%% 比值 %.3f | 2026占 %s" % (
            k, s["年化"] * 100, s["回落"] * 100, s["比值"], s["回本年數"], s["期末倍數"], db["拿掉的年"], db["年化"] * 100, db["回落"] * 100,
            db["比值"], s.get("2026貢獻占比（占全窗總獲利）")))
    for k in arms:
        print(k, "事件", full[k]["事件"])
    print("揭露", {y: rk[y]["揭露"] for y in years})
    print("V-IPO", {y: rk[y]["V-IPO前3"] for y in years})
    print("深度", {r["持有年"]: round(r["第1名年內最深（收盤÷買價−1）"], 4) for r in rows})
    print("曆年", {r["持有年"]: round(r["第1名曆年報酬（收盤→收盤，對帳用）"], 4) for r in rows})
    print("V-IPO 逐年", {r["持有年"]: (r["V-IPO第1名（對帳描述）"], round(r["V-IPO當年（對帳描述）"], 4)) for r in rows})
    for k in arms:
        print(k, "2026單一持股", full[k]["2026單一持股貢獻占比"], "拿掉2026", {x: full[k]["拿掉2026（描述）"][x] for x in ("年化", "回落", "比值", "回本年數")})
    print("V-IPO曆年", {r["持有年"]: round(r["V-IPO第1名曆年報酬（收盤→收盤）"], 4) for r in rows})
    for k in full:
        print(k, "高點", full[k]["高點日"], "谷底", full[k]["谷底日"], "回本日", full[k]["回本日"])
    print("資料尾", cal[tail].date(), gsrc)


if __name__ == "__main__":
    main()

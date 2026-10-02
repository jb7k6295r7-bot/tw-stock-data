# -*- coding: utf-8 -*-
"""交易紀錄檢驗工具（backtest/tradecheck.py）的試跑：營量 v1、營飆 v1 正式 T1 逐筆交易＋假訊號對照＋使用者持股。參考，⛔ 不計 N。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.tradecheck_trial

讀法（寫死於 2026-10-02（台北），在算任何數字之前）：
 T1 營量 v1 ＝ resultsYL_flowexit/trades_A_entries.csv.gz 策略「營量 v1」（r0 717 筆 ＝ 正式 T1 組合實際買進，閘③ ＝ audit_seed0）
    報酬 ＝ A_報酬（已扣來回 0.585%）；出場日 ＝ 引擎日曆[A_xpos]；A_xpos ≥ 日曆長 ⇒ 未平倉（照 T1 墊一根計值的那些）⇒ 不進統計
    營飆 v1 ＝ 同檔「營飆 v1」r0（第 0 顆種子的實際 173 筆）；200 顆合併不用（同一筆重複計）
    每筆投入資金：營量 1/20、營飆 1/10（正式檔數）
 T2 假訊號：每一筆真交易換成「同進場日、同出場日、從當天可交易的全部股票隨機抽一檔」（進場 ＝ 開盤、出場 ＝ 出場日收盤、扣 0.585%）
    母體 ＝ data.load_universe() 上市＋上櫃普通股（含已下市，興櫃排除），價格 ＝ rerun17.load_prices（同引擎：收盤還原 ffill、開盤原樣）
    可抽 ＝ 進場日開盤有限且 > 0；出場值 ＝ 出場日收盤（ffill ⇒ 持有中停牌／下市的，以最後收盤計，⛔ 不剔除，避免倖存者偏差）
    ⛔ 不用引擎價格表（921 檔）：那是「之後出過營量／營飆訊號的股票」，用了等於拿未來資訊挑母體
    抽 200 次：報裁決分佈；第 0 次寫成交易表給工具跑全套
    基準報酬 ＝ 同一筆的同進場日、同出場日、全部可交易股票的平均（等權）⇒ 超額 ＝ 報酬 − 基準
 T3 預期：假訊號的「超額」應判像運氣／負期望，判成統計優勢的比例應約 5% 以內；
    假訊號的「絕對報酬」若判成優勢，代表那是同期大盤漲（買什麼都賺），⛔ 不是工具壞掉 ⇒ 照實報
 T4 使用者持股：信箱 _持股/持股.csv（只讀）⇒ 全部未賣 ⇒ 只能列未平倉
 T5 兩欄對照示範（⛔ 不是實際成交）：同一批營量 r0 訊號，照規則 ＝ 正式出場（A）、另一欄 ＝ 飆股流程出場（B）
"""
from __future__ import annotations

import json
import os
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import tradecheck as TC

OUT = "backtest/resultsTradeCheck"
HOLD = "/mnt/c/SynologyDrive/跨線信箱/_持股/持股.csv"
NPL = 200
SEED = 20261002
FRAC = {"營量 v1": 0.05, "營飆 v1": 0.10}
TIME = "2026-10-02（台北）"


def log(m):
    print(f"[{time.strftime('%H:%M:%S')}] {m}", flush=True)


def main():
    os.makedirs(OUT, exist_ok=True)
    T0 = time.time()
    from backtest import data as D
    from backtest import rerun17 as RR
    RR.use_snapshot()                       # 同 listexit_lines.setup_t1（正式 T1 用的資料快照）
    cal = D.load_calendar(); n0 = len(cal)
    fe = json.load(open("backtest/resultsYL_flowexit/meta.json", encoding="utf-8"))
    assert str(cal[-1].date()) == fe["日曆尾"], f"日曆尾 {cal[-1].date()} ≠ flowexit {fe['日曆尾']}"
    uni = D.load_universe().set_index("stock_id")["market"]
    closes, opens = RR.load_prices(set(uni.index), cal, uni, "branch")
    log(f"價格 {len(closes)} 檔／母體 {len(uni)} 檔｜{time.time() - T0:.0f}s，日曆 {cal[0].date()}～{cal[-1].date()}（{n0}）")
    sids = sorted(closes)
    O = np.vstack([np.asarray(opens[s], float)[:n0] for s in sids])
    C = np.vstack([np.asarray(closes[s], float)[:n0] for s in sids])
    okO = np.isfinite(O) & (O > 0)

    PT = pd.read_csv("backtest/resultsYL_flowexit/trades_A_entries.csv.gz", dtype={"sid": str})
    PT = PT[PT["r"] == 0].reset_index(drop=True)
    meta = {"讀法寫死": TIME, "母體檔數": len(sids)}
    tables = {}
    for strat in ("營量 v1", "營飆 v1"):
        m = PT[PT["策略"] == strat].reset_index(drop=True)
        assert np.allclose(m["A_px30"], m["A_px70"]), "A 應為單一出場價"
        assert all(str(cal[int(a)].date()) == b for a, b in zip(m["e"], m["進場日"])), "進場位置與日曆對不上"
        closed = m["A_xpos"].to_numpy() < n0
        xd = [str(cal[int(x)].date()) if c else "" for x, c in zip(m["A_xpos"], closed)]
        df = pd.DataFrame({"代號": m["sid"], "進場日": m["進場日"], "進場價": m["bp"].map("{:.6f}".format),
                           "出場日": xd, "出場價": np.where(closed, m["A_px70"].map("{:.6f}".format), ""),
                           "報酬": np.where(closed, m["A_報酬"].map("{:.10f}".format), ""), "持有天數": np.where(closed, m["A_天"].astype(str), ""),
                           "標籤": strat})
        # 基準與假訊號
        e = m["e"].to_numpy(int); x = m["A_xpos"].to_numpy(int)
        bench = np.full(len(m), np.nan)
        elig = []
        for i in range(len(m)):
            if not closed[i]:
                elig.append(None); continue
            ok = okO[:, e[i]] & np.isfinite(C[:, x[i]])
            idx = np.flatnonzero(ok)
            g = C[idx, x[i]] / O[idx, e[i]] - 1 - TC.COST
            bench[i] = g.mean(); elig.append((idx, g))
        df["基準報酬"] = np.where(closed, pd.Series(bench).map("{:.10f}".format), "")
        tables[strat] = (m, df, elig, closed)
        df.to_csv(os.path.join(OUT, f"{strat.replace(' ', '')}_交易.csv"), index=False, encoding="utf-8-sig")
        allg = np.concatenate([v[1] for v in elig if v is not None])
        meta[f"{strat} 筆數"] = {"全部": len(m), "已平倉": int(closed.sum()), "未平倉": int((~closed).sum()),
                                "每筆可抽股票數中位": int(np.median([len(v[0]) for v in elig if v is not None])),
                                "可抽組合數": int(len(allg)), "極端（< −80% 或 > +500%）比例": float(np.mean((allg < -0.8) | (allg > 5)))}
        log(f"{strat}：{len(m)} 筆，已平倉 {closed.sum()}")

    reps, placebo_stats = {}, {}
    for strat in ("營量 v1", "營飆 v1"):
        m, df, elig, closed = tables[strat]
        c, op, nt, pa = TC.normalize(df.astype(str))
        reps[strat] = TC.analyze(c, f"{strat} 正式 T1（第 0 顆）", FRAC[strat], openp=op, notes=nt, paired=pa)
        log(f"{strat}：{TC.LEVELS[reps[strat]['level']][0]}｜超額 {TC.LEVELS[reps[strat]['excess']['level']][0]}")
        # 假訊號 200 次
        rng = np.random.default_rng(SEED + (0 if strat == "營量 v1" else 1))
        lv_abs, lv_ex, means, exmeans = [], [], [], []
        for k in range(NPL):
            pick_sid, ret = [], []
            for i in range(len(m)):
                if elig[i] is None:
                    pick_sid.append(""); ret.append(np.nan); continue
                idx, g = elig[i]
                j = int(rng.integers(len(idx)))
                pick_sid.append(sids[idx[j]]); ret.append(g[j])
            ret = np.asarray(ret)
            pdf = df.copy()
            pdf["代號"] = pick_sid
            pdf["報酬"] = np.where(closed, pd.Series(ret).map("{:.10f}".format), "")
            pdf["進場價"] = ""; pdf["出場價"] = ""; pdf["標籤"] = "假訊號"
            c, op, nt, pa = TC.normalize(pdf.astype(str))
            if k == 0:
                pdf.to_csv(os.path.join(OUT, f"假訊號_{strat.replace(' ', '')}_交易.csv"), index=False, encoding="utf-8-sig")
                rp = TC.analyze(c, f"假訊號（{strat} 同進出場日、隨機換股，第 0 次）", FRAC[strat], openp=op, notes=nt)
                reps[f"假訊號 {strat}"] = rp
            else:
                rp = TC.analyze(c, "p", FRAC[strat], B=2000, openp=op)
            lv_abs.append(rp["level"]); lv_ex.append(rp["excess"]["level"])
            means.append(rp["metrics"]["expectancy"]); exmeans.append(rp["excess"]["metrics"]["expectancy"])
            if k % 50 == 0:
                log(f"假訊號 {strat} {k}｜{time.time() - T0:.0f}s")
        real = reps[strat]
        placebo_stats[strat] = {
            "次數": NPL,
            "絕對裁決分佈": pd.Series(lv_abs).map(lambda v: TC.LEVELS[v][0]).value_counts().to_dict(),
            "超額裁決分佈": pd.Series(lv_ex).map(lambda v: TC.LEVELS[v][0]).value_counts().to_dict(),
            "絕對判統計優勢比例": float(np.mean([v == "edge" for v in lv_abs])),
            "超額判統計優勢比例": float(np.mean([v == "edge" for v in lv_ex])),
            "超額判脆弱或統計優勢比例": float(np.mean([v in ("edge", "fragile") for v in lv_ex])),
            "假訊號期望值中位": float(np.median(means)), "假訊號期望值 p10～p90": [float(np.quantile(means, .1)), float(np.quantile(means, .9))],
            "假訊號超額中位": float(np.median(exmeans)),
            "真交易期望值": real["metrics"]["expectancy"], "真交易超額": real["excess"]["metrics"]["expectancy"],
            "真交易期望值勝過幾成假訊號": float(np.mean(np.asarray(means) < real["metrics"]["expectancy"])),
        }
        log(json.dumps(placebo_stats[strat], ensure_ascii=False))

    # 合併（逐標籤＋反事實）
    comb = pd.concat([tables["營量 v1"][1], tables["營飆 v1"][1]], ignore_index=True)
    c, op, nt, pa = TC.normalize(comb.astype(str))
    reps["合併"] = TC.analyze(c, "營量＋營飆合併（第 0 顆；逐標籤示範）", 0.05, openp=op, notes=nt)

    # 兩欄對照示範：A（正式）vs B（流程）
    m, df, elig, closed = tables["營量 v1"]
    both = closed & (m["B_xpos"].to_numpy() < n0)
    dd = df.copy()
    dd["照規則報酬"] = np.where(closed, m["A_報酬"].map("{:.10f}".format), "")
    dd["實際報酬"] = np.where(both, m["B_報酬"].map("{:.10f}".format), "")
    dd = dd.drop(columns=["報酬", "基準報酬"])
    c, op, nt, pa = TC.normalize(dd.astype(str))
    pr = TC.paired_test(c[np.isfinite(c["act_ret"])])
    meta["兩欄示範"] = {k: v for k, v in pr.items()}

    # 使用者持股
    hc, hop, hnt, hpa = TC.load_csv(HOLD)
    reps["持股"] = TC.analyze(hc, "使用者實際持股（_持股/持股.csv）", 0.1, openp=hop, notes=hnt)
    meta["持股"] = {"已平倉": int(len(hc)), "未平倉": int(len(hop)), "其中缺買進日或價": reps["持股"].get("open_missing", 0)}

    chk = TC.selfcheck()
    meta["check 全過"] = chk["全過"]
    with open(os.path.join(OUT, "check.json"), "w", encoding="utf-8") as f:
        json.dump(chk, f, ensure_ascii=False, indent=1, default=TC._json_default)
    with open(os.path.join(OUT, "reports.json"), "w", encoding="utf-8") as f:
        json.dump({"meta": meta, "placebo": placebo_stats, "reports": reps}, f, ensure_ascii=False, indent=1, default=TC._json_default)
    with open(os.path.join(OUT, "reports.txt"), "w", encoding="utf-8") as f:
        for k, r in reps.items():
            f.write(TC.text_report(r) + "\n\n")
    page(reps, placebo_stats, meta, chk, pr)
    log(f"完成 {time.time() - T0:.0f}s")


def page(reps, PS, meta, chk, pr):
    e = TC.html.escape
    L = lambda k: TC.LEVELS[reps[k]["level"]][0]
    LX = lambda k: TC.LEVELS[reps[k]["excess"]["level"]][0]
    y, f = reps["營量 v1"], reps["營飆 v1"]
    py, pf = PS["營量 v1"], PS["營飆 v1"]
    fmt = TC._p
    concl = [
        f"<li><b>營量 v1</b>：{TC.badge(y['level'])}　{y['metrics']['n']} 筆，每筆平均 {fmt(y['metrics']['expectancy'], 2)}；"
        f"扣掉同期隨便買的平均後，超額 {fmt(y['excess']['metrics']['expectancy'], 2)}，判 {TC.badge(y['excess']['level'])}</li>",
        f"<li><b>營飆 v1</b>：{TC.badge(f['level'])}　{f['metrics']['n']} 筆，每筆平均 {fmt(f['metrics']['expectancy'], 2)}；"
        f"超額 {fmt(f['excess']['metrics']['expectancy'], 2)}，判 {TC.badge(f['excess']['level'])}</li>",
        f"<li><b>假訊號</b>（同進出場日、隨機換股，各抽 {py['次數']} 次）：超額判成統計優勢 營量 {py['超額判統計優勢比例']:.1%}、營飆 {pf['超額判統計優勢比例']:.1%}"
        f"（應約 5% 以內）；絕對報酬判成統計優勢 營量 {py['絕對判統計優勢比例']:.0%}、營飆 {pf['絕對判統計優勢比例']:.0%}——那是同期大盤漲，買什麼都賺，所以要看超額。</li>",
        "<li>⚠ 營量、營飆是<b>回測交易</b>：規則是看過這段歷史才定的，又是從很多試過的做法裡留下來的 ⇒ 工具的樣本外切點不是真的沒看過的資料。"
        "這裡的「統計優勢」只說明工具判得出來，⛔ 不取代回測線對它們的既有結論；真正的檢驗是前瞻紀錄累積的實際交易。</li>",
        f"<li><b>你的持股</b>：{meta['持股']['未平倉']} 檔都還沒賣（其中 {meta['持股']['其中缺買進日或價']} 檔缺買進日／價），未平倉不能檢驗；賣出後補出場日、出場價就能跑。</li>",
        f"<li><b>工具自我查核</b>：{'全部通過' if chk['全過'] else '⚠ 有沒過的項目'}（有優勢 ⇒ 判優勢、均值 0 ⇒ 不判、負期望 ⇒ 判負期望；均值 0 重抽 1,000 次誤判 "
        f"{chk[[k for k in chk if k.startswith('④')][0]]['常態']['兩者都顯著']:.1%}）。</li>",
    ]
    intro = (f'<p class="mut">回測線 {TIME}｜參考，不計 N｜照開源專案「反詐投資王」（mars-tw/anti-gambling-trader-tw）的檢驗流程自己寫的工具，先拿正式回測的逐筆交易試跑。</p>'
             f'<div class="card"><p class="big">結論</p><ul>{"".join(concl)}</ul></div>')
    sec = ["<h2>假訊號對照</h2>"]
    sec.append(TC._tbl(["", "營量 v1", "營飆 v1"], [
        ["真交易每筆平均", fmt(py["真交易期望值"], 2), fmt(pf["真交易期望值"], 2)],
        ["假訊號每筆平均（中位）", fmt(py["假訊號期望值中位"], 2), fmt(pf["假訊號期望值中位"], 2)],
        ["假訊號 p10～p90", f"{fmt(py['假訊號期望值 p10～p90'][0], 2)}～{fmt(py['假訊號期望值 p10～p90'][1], 2)}",
         f"{fmt(pf['假訊號期望值 p10～p90'][0], 2)}～{fmt(pf['假訊號期望值 p10～p90'][1], 2)}"],
        ["真交易勝過幾成假訊號", TC._pp(py["真交易期望值勝過幾成假訊號"]), TC._pp(pf["真交易期望值勝過幾成假訊號"])],
        ["假訊號絕對報酬判統計優勢", TC._pp(py["絕對判統計優勢比例"], 1), TC._pp(pf["絕對判統計優勢比例"], 1)],
        ["假訊號超額判統計優勢", TC._pp(py["超額判統計優勢比例"], 1), TC._pp(pf["超額判統計優勢比例"], 1)],
        ["假訊號超額判脆弱或統計優勢", TC._pp(py["超額判脆弱或統計優勢比例"], 1), TC._pp(pf["超額判脆弱或統計優勢比例"], 1)],
    ]))
    sec.append('<p class="mut">只看「賺不賺」，同期隨便買也會被判有優勢；所以本工具可以另給「基準報酬」欄，檢驗「贏不贏同期隨便買」。'
               "營量、營飆要看的是超額那一行。</p>")
    sec.append("<h2>營量 v1</h2>" + TC.html_section(y))
    sec.append("<h2>營飆 v1</h2>" + TC.html_section(f))
    sec.append("<h2>假訊號（第 0 次，完整檢驗）</h2>" + TC.html_section(reps["假訊號 營量 v1"], show_detail=False)
               + TC.html_section(reps["假訊號 營飆 v1"], show_detail=False))
    sec.append("<h2>合併與逐標籤</h2>" + TC.html_section(reps["合併"]))
    word = ("改用流程出場比正式" + ("多賺" if pr["mean"] > 0 else "少賺") + f" {abs(pr['mean']):.2%}／筆，" + ("不像運氣" if pr["significant"] else "和運氣分不開"))
    sec.append(f"<h2>兩欄對照示範</h2><p>⛔ 這不是實際成交：目前沒有實際成交紀錄，先拿同一批營量訊號的「正式出場」當照規則、「飆股流程出場」當另一欄，驗工具的配對比較。"
               f"{pr['n']} 筆：{e(word)}（t p＝{TC._f(pr['p_t'], 3)}、bootstrap p＝{TC._f(pr['p_boot'], 3)}）。前瞻紀錄有「實際」欄後，同一段就是「實際比規則多賺或少賺」。</p>")
    sec.append("<h2>你的持股</h2>" + TC.html_section(reps["持股"], show_detail=False))
    with open(os.path.join(OUT, "交易紀錄檢驗（營量營飆試跑）.html"), "w", encoding="utf-8") as fh:
        fh.write(TC.html_page("交易紀錄檢驗（營量營飆試跑）", "".join(sec), intro))


if __name__ == "__main__":
    main()

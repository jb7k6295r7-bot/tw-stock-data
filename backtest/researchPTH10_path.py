# -*- coding: utf-8 -*-
"""52 週新高 10 檔版（resultsPTHn N＝10 ＝ resultsPTHpf 10 檔版）逐筆「持有中路徑」描述——回測線計算子代理（2026-10-20）。
使用者看了「報酬靠少數大賺」後問：「有先跌後大漲的嗎？」
⛔ 描述、不計 N、不判；看過結果才問 ⇒ 結果句必附「描述，不是買賣建議；看過結果才問」。
⛔ 只計算：不 commit、不改既有檔；researchPTHpf（build_world、COST、TYPN）⛔ 只 import。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchPTH10_path
    對帳：PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchPTH10_path_check
輸出 backtest/resultsPTH10path/：path_trades.csv、top10.csv、groups.csv、deep15.csv、stop15.csv、path.json、run.log

讀法（★ 執行者定）：
 P1 交易 ＝ resultsPTHn/trades_<世界>_N10.csv.gz（不加滑價）每一列；只算已出場（賣出日非空）；依買進日歸段（researchPTHn.trade_dist 同式：
    主 探索／確認、早年 早年；主世界 2016-03～2017-03-01 買進、段外的筆不計，另報筆數）。
 P2 價格讀法 ⛔ 不另寫：世界 ＝ researchPTHpf.build_world（含息還原快取收盤 ffill ＝ W["CM"]、壞根強制出場已在出場日內）；
    買價 ＝ 交易檔「市值基準價」（＝ 快取還原開盤 O[買進日]，本支逐筆驗）；路徑 ＝ CM[股, 日] ÷ 買價 − 1（＝ 引擎逐日市值式）。
    閘：CM[股, 賣出日] ÷ 買價 − 1 ＝ R用（≤1e−9）、賣出日 ＝ 排程賣出日、買價 ＝ O[買進日]；不過 ⇒ 中止。
 P3 ★「持有中」＝ 買進日收盤 … 賣出日前一日收盤（出場日收盤即出場價，不算浮動）；買進當日即賣（區間空）⇒ 以出場日收盤代。
    最大浮虧 ＝ min(0, 區間最低收盤 ÷ 買價 − 1)；最大浮盈 ＝ max(0, 區間最高收盤 ÷ 買價 − 1)；
    發生在第幾個交易日 ＝ 日曆位置差 ＋ 1（買進日 ＝ 第 1 日；日曆 ＝ 世界交易日曆，該股停牌日以 ffill 收盤計）。另存含出場日版本。
    只看收盤（⛔ 盤中低點未計）。淨報酬 ＝ R用 − 0.585%（researchPTHn 同式）。
 P4 分組：各段內依淨報酬排序（同值依交易檔列序），前 ceil(10%) 筆 ＝ 前 10%（＝ researchPTHn.trade_dist「前10%筆數」）、後 ceil(10%) 筆 ＝ 後 10%、其餘中間。
    另報主世界兩段合併。門檻判定：最大浮虧 ≤ −10%／−15%／−20%（含等號）。
 P5 反向：最大浮虧 ≤ −15% 的筆：最後淨報酬 ＞0、＞＋30%、≤ −15% 的比例。
 P6 ★ −15% 停損對照（只數，⛔ 不模擬組合）：持有中收盤曾 ≤ −15% 且最後屬前 10%（另報淨報酬 ＞＋30%）的筆數；
    其淨報酬和 ÷ 段內全部淨報酬和（等權，＝ researchPTHn「前10%貢獻占比」分母）、÷ 段內獲利筆淨報酬和；另報金額加權（金額×淨報酬）。
"""
from __future__ import annotations

import gzip
import json
import math
import os
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import researchPTHpf as M                     # noqa: E402  ⛔ 只 import
from backtest import researchPTHpf_check as PC              # noqa: E402  rd
from backtest import researchAddOn as RA                    # noqa: E402

OUT = "backtest/resultsPTH10path"
SRC = "backtest/resultsPTHn"
COST = M.COST
SENT = "描述，不是買賣建議；看過結果才問"
THR = (-0.10, -0.15, -0.20)


def paths(W, df, wn):
    CM = W["CM"]; O = np.asarray(W["O"], float); ix = W["ix"]; dates = W["dates"]
    dpos = {d: i for i, d in enumerate(dates)}
    names = W.get("names", {})
    rows = []; bad = {"買價≠O": 0, "賣價閘": 0, "賣出≠排程": 0}
    for r_, z in enumerate(df.itertuples(index=False)):
        if z.賣出日 == "":
            continue
        sid = str(z.sid); j = ix[sid]; e = dpos[z.買進日]; s = dpos[z.賣出日]
        ep = float(z.市值基準價)
        if ep != O[j, e]:
            bad["買價≠O"] += 1
        if abs(CM[j, s] / ep - 1.0 - float(z.R用)) > 1e-9:
            bad["賣價閘"] += 1
        if z.賣出日 != z.排程賣出日:
            bad["賣出≠排程"] += 1
        seg = CM[j, e:s] / ep - 1.0
        empty = len(seg) == 0
        if empty:
            seg = CM[j, s:s + 1] / ep - 1.0
        k_lo = int(np.argmin(seg)); k_hi = int(np.argmax(seg))
        seg2 = CM[j, e:s + 1] / ep - 1.0
        lo = float(seg[k_lo]); hi = float(seg[k_hi])
        net = float(z.R用) - COST
        rows.append({"世界": wn, "列": r_, "sid": sid, "名稱": names.get(sid, ""), "買進日": z.買進日, "賣出日": z.賣出日,
                     "持有交易日": int(s - e), "出場種類": z.出場種類, "金額": float(z.金額), "買價": ep, "R用": float(z.R用), "淨報酬": net,
                     "最大浮虧": min(0.0, lo), "最低收盤報酬": lo, "最大浮虧日序": (int(k_lo + 1) if not empty else int(s - e + 1)),
                     "最大浮虧日": dates[e + k_lo] if not empty else dates[s],
                     "最大浮盈": max(0.0, hi), "最高收盤報酬": hi, "最大浮盈日序": (int(k_hi + 1) if not empty else int(s - e + 1)),
                     "最大浮盈日": dates[e + k_hi] if not empty else dates[s],
                     "含出場日最低": float(seg2.min()), "含出場日最高": float(seg2.max()), "區間空(當日買賣)": empty})
    if any(bad.values()):
        raise SystemExit(f"⛔ {wn} 價格閘不過 {bad}")
    return pd.DataFrame(rows)


def seg_of(W, wn, P):
    cal_d = {d: i for i, d in enumerate(W["dates"])}
    t = P["買進日"].map(cal_d).to_numpy()
    lab = np.full(len(P), "", object)
    for sg, (x, y) in W["segp"].items():
        lab[(t >= x) & (t <= y)] = sg
    return lab


def grouping(P):
    """段內：依淨報酬由高往低（同值依列序，stable）⇒ 前／中／後。"""
    g = np.full(len(P), "中間80%", object)
    v = P["淨報酬"].to_numpy(); n = len(v); k = max(1, math.ceil(0.1 * n))
    o = np.argsort(-v, kind="stable")
    g[o[:k]] = "前10%"; g[o[n - k:]] = "後10%"
    return g, k


def grp_stats(D):
    o = {"筆數": int(len(D))}
    for th in THR:
        o[f"曾≤{int(th * 100)}%"] = float((D["最大浮虧"] <= th + 1e-12).mean()) if len(D) else np.nan
        o[f"曾≤{int(th * 100)}%筆"] = int((D["最大浮虧"] <= th + 1e-12).sum())
    o["最大浮虧中位"] = float(D["最大浮虧"].median()) if len(D) else np.nan
    o["最大浮虧日序中位"] = float(D["最大浮虧日序"].median()) if len(D) else np.nan
    o["淨報酬中位"] = float(D["淨報酬"].median()) if len(D) else np.nan
    o["最大浮盈中位"] = float(D["最大浮盈"].median()) if len(D) else np.nan
    return o


def deep_stats(D):
    d = D[D["最大浮虧"] <= -0.15 + 1e-12]
    n = len(d)
    return {"筆數(總)": int(len(D)), "曾≤-15%筆": int(n), "占全部": float(n / len(D)) if len(D) else np.nan,
            "最後賺(>0)": float((d["淨報酬"] > 0).mean()) if n else np.nan, "最後賺筆": int((d["淨報酬"] > 0).sum()),
            "大賺(>+30%)": float((d["淨報酬"] > 0.30).mean()) if n else np.nan, "大賺筆": int((d["淨報酬"] > 0.30).sum()),
            "收在≤-15%": float((d["淨報酬"] <= -0.15).mean()) if n else np.nan, "收在≤-15%筆": int((d["淨報酬"] <= -0.15).sum()),
            "-15%~0": float(((d["淨報酬"] > -0.15) & (d["淨報酬"] <= 0)).mean()) if n else np.nan,
            "淨報酬中位": float(d["淨報酬"].median()) if n else np.nan,
            "對照:未曾≤-15%者最後賺": float((D.loc[D["最大浮虧"] > -0.15 + 1e-12, "淨報酬"] > 0).mean()) if len(D) > n else np.nan,
            "對照:未曾≤-15%者大賺(>+30%)": float((D.loc[D["最大浮虧"] > -0.15 + 1e-12, "淨報酬"] > 0.30).mean()) if len(D) > n else np.nan}


def stop_stats(D):
    hit = D["最大浮虧"] <= -0.15 + 1e-12
    v = D["淨報酬"]; pnl = D["金額"] * v
    tot = v.sum(); pos = v[v > 0].sum(); ptot = pnl.sum(); ppos = pnl[pnl > 0].sum()
    o = {"筆數": int(len(D)), "前10%筆": int((D["組"] == "前10%").sum())}
    for tag, m in (("前10%", D["組"] == "前10%"), (">+30%", v > 0.30)):
        mm = hit & m
        o[f"{tag}中曾≤-15%筆"] = int(mm.sum()); o[f"{tag}筆"] = int(m.sum())
        o[f"{tag}中曾≤-15%：淨報酬和÷全部淨報酬和"] = float(v[mm].sum() / tot) if tot else np.nan
        o[f"{tag}中曾≤-15%：淨報酬和÷獲利筆淨報酬和"] = float(v[mm].sum() / pos) if pos else np.nan
        o[f"{tag}中曾≤-15%：金額加權÷全部"] = float(pnl[mm].sum() / ptot) if ptot else np.nan
        o[f"{tag}中曾≤-15%：金額加權÷獲利筆"] = float(pnl[mm].sum() / ppos) if ppos else np.nan
    o["全部淨報酬和(等權)"] = float(tot); o["獲利筆淨報酬和(等權)"] = float(pos)
    return o


def run(log):
    T0 = time.time(); os.makedirs(OUT, exist_ok=True)
    J = {"題": "使用者問「有先跌後大漲的嗎？」：52 週新高 10 檔版逐筆持有中最大浮虧／浮盈", "身分": "描述（⛔ 不判、不計 N）", "結果句必附": SENT,
         "開跑": M.now_tpe(), "閘": {}, "分組": [], "反向": [], "停損對照": [], "段外筆": {}}
    ALL = []
    for wn in ("主", "早年"):
        W = M.build_world(wn, log)
        df = PC.rd(os.path.join(SRC, f"trades_{wn}_N10.csv.gz"))
        df["sid"] = df["sid"].astype(str)
        P = paths(W, df, wn)
        J["閘"][wn] = f"已出場 {len(P)} 筆：買價 ＝ O[買進日]、CM[賣出日]÷買價−1 ＝ R用（≤1e−9）、賣出日 ＝ 排程賣出日 全過；未出場 {int((df['賣出日'] == '').sum())} 筆不計"
        P["段"] = seg_of(W, wn, P)
        J["段外筆"][wn] = int((P["段"] == "").sum())
        P = P[P["段"] != ""].copy()
        P["組"] = ""; P["前10%筆數(段)"] = 0
        for sg in W["segp"]:
            m = (P["段"] == sg).to_numpy()
            g, k = grouping(P[m])
            P.loc[m, "組"] = g; P.loc[m, "前10%筆數(段)"] = k
        ALL.append(P)
        log(f"[{wn}] 已出場 {len(P)} 筆（段外 {J['段外筆'][wn]}）｜{time.time() - T0:.0f}s")
        del W
    A = pd.concat(ALL, ignore_index=True)
    # 主兩段合併：分組另算
    mm = A["世界"] == "主"
    gm, km = grouping(A[mm])
    A["組(主合併)"] = ""
    A.loc[mm, "組(主合併)"] = gm
    A.to_csv(os.path.join(OUT, "path_trades.csv"), index=False, float_format="%.10g", encoding="utf-8-sig")
    top = A[A["組"] == "前10%"].sort_values(["世界", "段", "淨報酬"], ascending=[False, True, False]).copy()
    top["曾跌破買價"] = top["最低收盤報酬"] < 0
    nb = ~top["曾跌破買價"]
    top["最大浮虧日序"] = top["最大浮虧日序"].astype(object); top["最大浮虧日"] = top["最大浮虧日"].astype(object)
    top.loc[nb, "最大浮虧日序"] = "—"; top.loc[nb, "最大浮虧日"] = "未跌破買價"
    top[["世界", "段", "sid", "名稱", "買進日", "賣出日", "持有交易日", "出場種類", "淨報酬", "最大浮虧", "曾跌破買價", "最大浮虧日序", "最大浮虧日", "最大浮盈", "最大浮盈日序"]].to_csv(
        os.path.join(OUT, "top10.csv"), index=False, float_format="%.4f", encoding="utf-8-sig")
    views = [("主", "探索", (A["世界"] == "主") & (A["段"] == "探索"), "組"), ("主", "確認", (A["世界"] == "主") & (A["段"] == "確認"), "組"),
             ("主", "探索＋確認", mm, "組(主合併)"), ("早年", "早年", A["世界"] == "早年", "組")]
    G = []; DP = []; ST = []
    for wn, sg, m, gc in views:
        D = A[m].copy(); D["組"] = D[gc]
        for gname in ("前10%", "中間80%", "後10%", "全部"):
            sub = D if gname == "全部" else D[D["組"] == gname]
            G.append({"世界": wn, "段": sg, "組": gname, **grp_stats(sub)})
        DP.append({"世界": wn, "段": sg, **deep_stats(D)})
        ST.append({"世界": wn, "段": sg, **stop_stats(D)})
    GD = pd.DataFrame(G); DD = pd.DataFrame(DP); SD = pd.DataFrame(ST)
    GD.to_csv(os.path.join(OUT, "groups.csv"), index=False, float_format="%.4f", encoding="utf-8-sig")
    DD.to_csv(os.path.join(OUT, "deep15.csv"), index=False, float_format="%.4f", encoding="utf-8-sig")
    SD.to_csv(os.path.join(OUT, "stop15.csv"), index=False, float_format="%.4f", encoding="utf-8-sig")
    J["分組"] = G; J["反向"] = DP; J["停損對照"] = ST
    # 對 researchPTHn trade_dist（N=10）
    TD = pd.read_csv(os.path.join(SRC, "trade_dist.csv"))
    rec = {}
    for wn, sg in (("主", "探索"), ("主", "確認"), ("早年", "早年")):
        r = TD[(TD["世界"] == wn) & (TD["臂"] == "N=10") & (TD["段"] == sg)].iloc[0]
        D = A[(A["世界"] == wn) & (A["段"] == sg)]
        v = D["淨報酬"]; k = int((D["組"] == "前10%").sum())
        ok = (len(D) == int(r["筆數"]) and k == int(r["前10%筆數"]) and abs(v.median() - r["中位"]) < 1e-6 * max(1, abs(r["中位"])) + 1e-7
              and abs(v[D["組"] == "前10%"].sum() / v.sum() - r["前10%貢獻占比(等權)"]) < 1e-5)
        rec[f"{wn}|{sg}"] = {"筆數": [len(D), int(r["筆數"])], "前10%筆": [k, int(r["前10%筆數"])], "中位": [float(v.median()), float(r["中位"])],
                             "前10%占比": [float(v[D["組"] == "前10%"].sum() / v.sum()), float(r["前10%貢獻占比(等權)"])], "相符": bool(ok)}
        if not ok:
            raise SystemExit(f"⛔ {wn}/{sg} 與 resultsPTHn trade_dist 不符 {rec[f'{wn}|{sg}']}")
    J["對帳_trade_dist"] = rec
    pd.set_option("display.width", 250); pd.set_option("display.max_columns", 40)
    log("[前10%]\n" + top[["世界", "段", "sid", "名稱", "買進日", "賣出日", "淨報酬", "最大浮虧", "最大浮虧日序", "最大浮盈"]].to_string())
    log("[分組]\n" + GD.to_string())
    log("[反向]\n" + DD.to_string())
    log("[停損]\n" + SD.T.to_string())
    log(f"[對帳 trade_dist] {json.dumps(rec, ensure_ascii=False)}")
    J["耗時秒"] = round(time.time() - T0); J["完成"] = M.now_tpe()
    json.dump(J, open(os.path.join(OUT, "path.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    log(f"[完] {J['耗時秒']}s")


def main():
    os.makedirs(OUT, exist_ok=True)
    run(RA.log_to(os.path.join(OUT, "run.log")))


if __name__ == "__main__":
    main()

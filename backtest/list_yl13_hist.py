# -*- coding: utf-8 -*-
"""營量 v1 歷史名單 2025-08～2026-06 ＋ K 線圖（裁定 seq263 §二；使用者 09-28 要的）。回測線，2026-09-28。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.list_yl13_hist
    查核：PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.list_yl13_hist_check

⛔ 描述性名單，不是新回測、不改任何判定、不計 N。
正式跑法 ＝ researchT1fix #13 T1 版（commit 1e7229c101）：researchT1fix.build_ctx(True)（AND 資料尾截斷補回）、
  simulate_mtm(sig13, "H60", 20, default_rng(7000＋0), ..., log=[], d_max=None, pick="relvol", queue_days=0, stop_force=SF)
  ⭐ 停止交易強制出場：開；relvol 排序、不抽籤 ⇒ 種子無影響（取種子 0）
閘門：本檔重跑的權益 ＝ resultsT1fix/seeds.csv.gz（c13｜t1｜r＝0）逐位元（cagr／mdd／vol repr、first／end／trades、eq_sha）；不同 ⇒ 停
名單取引擎 audit 的實際買賣（進場日 2025-08-01～2026-06-30）；未入選 ＝ 同期引擎可用候選裡沒買到的（報酬照 H60 訊號表 g_H60）
輸出 backtest/resultsYLlist/
"""
from __future__ import annotations

import hashlib
import html
import json
import os
import time

import numpy as np
import pandas as pd

from . import researchT1fix as RT
from . import research11 as R
from . import rerun17 as RR
from . import data as D
from . import chart_svg as CS

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "resultsYLlist")
D0, D1 = "2025-08-01", "2026-06-30"
STAMP = "20260928"
SEED = 0
HOLD = 60
F_LIST = f"營量v1名單_2025-08至2026-06_{STAMP}.csv"
F_REST = f"營量v1未入選候選_2025-08至2026-06_{STAMP}.csv"
F_MD = f"營量v1名單摘要_{STAMP}.md"
F_HTML = f"營量v1_K線圖_2025-08至2026-06_{STAMP}.html"
HELD = "持有中（以 9/24 收盤計）"
WHY = {"a": "空槽不足（當日 relvol 名次在可買數之後）", "c": "已持有同一檔", None: "當日無空槽（20 槽全滿）"}


def _sha(eq):
    return hashlib.sha256(np.asarray(eq, float).tobytes()).hexdigest()[:16]


def raw_px(sid, mk):
    p = os.path.join(D.DATA, "stocks", f"{sid}.csv")
    r = pd.read_csv(p, dtype={"stock_id": str, "date": str}, usecols=["date", "open", "close"])
    r = r.drop_duplicates("date").set_index("date")
    for c in ("open", "close"):
        r[c] = pd.to_numeric(r[c], errors="coerce")
    return r


def main():
    t00 = time.time()
    os.makedirs(OUT, exist_ok=True)
    ctx = RT.build_ctx(True)
    cal = ctx["cal"]; NC = len(cal); NP = ctx["ncal"]; w0, w1 = ctx["w0"], ctx["w1"]
    assert NP == NC + 1 and str(cal[-1].date()) == "2026-09-24", (NP, NC, cal[-1])
    assert abs(R.COST - 0.00585) < 1e-15, R.COST
    mk = ctx["mk"]; closes, opens = ctx["closes"], ctx["opens"]
    sig = ctx["sig13"]
    SF = R.stop_force_days(R.valid_from_data(sorted(closes), mk, cal), w1)
    au, lg = [], []
    o = R.simulate_mtm(sig, "H60", 20, np.random.default_rng(RR.P1_SEED0 + SEED), closes, opens, NP,
                       log=lg, d_max=None, pick="relvol", queue_days=0, return_equity=True, audit=au, stop_force=SF)
    eq = np.asarray(o["equity"], float)
    c_, m_, v_ = RR.win_metrics(eq, o["first"], o["end"], w0, w1)
    mine = {"cagr": float(c_), "mdd": float(m_), "vol": float(v_), "first": int(o["first"]), "end": int(o["end"]),
            "trades": int(o["trades"]), "eq_sha": _sha(eq), "sf_n": int(o["x_stop_force_n"])}
    ref = pd.read_csv(os.path.join(HERE, "resultsT1fix", "seeds.csv.gz"), dtype={"eq_sha": str}, float_precision="round_trip")
    ref = ref[(ref["key"] == "c13") & (ref["var"] == "t1") & (ref["r"] == SEED)].iloc[0]
    gate = {k: (repr(mine[k]) == repr(float(ref[k])) if k in ("cagr", "mdd", "vol") else
                (str(mine[k]) == str(ref[k]) if k == "eq_sha" else int(mine[k]) == int(ref[k])))
            for k in ("cagr", "mdd", "vol", "first", "end", "trades", "eq_sha", "sf_n")}
    gate_ok = all(gate.values())
    G = {"閘門": "本檔重跑 #13 T1 種子 0 ＝ resultsT1fix/seeds.csv.gz（c13｜t1｜r＝0）逐位元", "全過": gate_ok, "逐欄": gate,
         "本檔": mine, "對照": {k: (ref[k] if k == "eq_sha" else float(ref[k])) for k in mine}}
    print(f"[閘門] {json.dumps(G, ensure_ascii=False, default=str)}", flush=True)
    json.dump(G, open(os.path.join(OUT, "gate.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    if not gate_ok:
        raise SystemExit("⛔ 閘門不過：重跑權益與 resultsT1fix 不同 ⇒ 停")

    # ── 引擎可用候選（＝ simulate_mtm 內部的 d）與當日排名
    d = sig[["sid", "entry_pos", "xpos_H60", "g_H60", "relvol", "month"]].copy()
    d["_ord"] = np.arange(len(d))
    elig = d["xpos_H60"].ge(0) & d[["sid", "entry_pos", "xpos_H60", "g_H60"]].notna().all(axis=1)
    d["_rk"] = np.where(d["relvol"].notna(), d["relvol"], -np.inf)
    E = d[elig].sort_values(["entry_pos", "_rk", "_ord"], ascending=[True, False, True], kind="stable").copy()
    E["當日候選排名"] = E.groupby("entry_pos").cumcount() + 1
    E["當日候選數"] = E.groupby("entry_pos")["sid"].transform("size")
    E["進場日"] = [str(cal[int(t)].date()) for t in E["entry_pos"]]
    inr = (E["進場日"] >= D0) & (E["進場日"] <= D1)
    E = E[inr].copy()
    E["月"] = E["進場日"].str[:7]
    E["該月候選數"] = E.groupby("月")["sid"].transform("size")
    X = d[~elig].copy()
    X["進場日"] = [str(cal[int(t)].date()) for t in X["entry_pos"]]
    X = X[(X["進場日"] >= D0) & (X["進場日"] <= D1)]
    print(f"[候選] 期間引擎可用 {len(E)} 列；引擎排除（出場日缺、非資料尾截斷）{len(X)} 列", flush=True)

    # ── audit ⇒ 逐筆成交
    AU = pd.DataFrame(au)
    AU.to_csv(os.path.join(OUT, "audit_seed0.csv.gz"), index=False, float_format="%.17g")
    if "kind" in AU and AU["kind"].notna().any():
        raise SystemExit(f"⛔ audit 有 kind（加減碼等）：{AU['kind'].dropna().unique()}")
    openb = {}; T = []
    for a in au:
        if a["side"] == "buy":
            assert a["sid"] not in openb
            openb[a["sid"]] = a
        else:
            b = openb.pop(a["sid"])
            T.append({"sid": a["sid"], "t_in": int(b["t"]), "ep": float(b["px"]), "amt": float(b["amt"]),
                      "t_out": int(a["t"]), "xp": float(a["px"]), "gross": float(a["amt"]) / float(b["amt"]) - 1.0})
    assert not openb, f"⛔ audit 有未平倉 {list(openb)[:5]}"
    T = pd.DataFrame(T)
    T["進場日"] = [str(cal[t].date()) for t in T["t_in"]]
    T = T[(T["進場日"] >= D0) & (T["進場日"] <= D1)].reset_index(drop=True)
    key = E.set_index(["sid", "entry_pos"])
    stocks = pd.read_csv(os.path.join(D.DATA, "meta", "stocks.csv"), dtype=str).drop_duplicates("stock_id").set_index("stock_id")
    from . import gate_b_status as GB
    fut, basis = GB.future_trading_days(cal, 2 * HOLD)
    RAW, STK = {}, {}

    def stk(s):
        if s not in STK:
            STK[s] = D.load_stock(s, mk.get(s, "twse"), cal)
            RAW[s] = raw_px(s, mk)
        return STK[s], RAW[s]

    def rawv(s, t, col):
        r = RAW[s]; ds = str(cal[t].date())
        return float(r.at[ds, col]) if ds in r.index and np.isfinite(r.at[ds, col]) else np.nan

    def est_exit(s, t_in):
        st, _ = stk(s)
        nb = int(st.df["traded"].to_numpy()[t_in:].sum())
        rem = HOLD - nb
        return (str(fut[rem - 1].date()) + "（推估" + ("，未公告休市只扣週末 ⇒ 實際只會更晚" if "只扣週末" in basis[rem - 1] else "") + "）") if rem >= 1 else ""

    rows = []
    for tr in T.itertuples():
        s, t_in, t_out = tr.sid, tr.t_in, tr.t_out
        k = key.loc[(s, t_in)]
        xpos = int(k["xpos_H60"]); stk(s)
        if t_out == NC:                                   # T1 墊檔日 ⇒ 資料尾還持有
            assert xpos == NC
            how, st_, xref, xdate = "資料尾：以 2026-09-24 收盤計（⛔ 未賣）", HELD, NC - 1, "2026-09-24"
            raw_out = rawv(s, NC - 1, "close")
        elif s in SF and t_out == SF[s] + 1 and t_out < xpos:
            L = SF[s]
            how, st_, xref, xdate = f"停止交易強制出場（以 {cal[L].date()} 最後收盤價）", "已出場", t_out, str(cal[t_out].date())
            raw_out = rawv(s, L, "close")
        else:
            assert t_out == xpos, (s, t_in, t_out, xpos)
            how, st_, xref, xdate = "H60 到期（第 60 根收盤）", "已出場", t_out, str(cal[t_out].date())
            raw_out = rawv(s, t_out, "close")
        rows.append({"進場日": tr.進場日, "代號": s, "名稱": stocks["name"].get(s, ""), "市場": mk.get(s, ""),
                     "進場價_還原": tr.ep, "進場價_原始": rawv(s, t_in, "open"),
                     "出場日": xdate, "出場價_還原": tr.xp, "出場價_原始": raw_out, "出場說明": how,
                     "報酬_扣成本_pct": (tr.gross - R.COST) * 100, "毛報酬_pct": tr.gross * 100,
                     "relvol": float(k["relvol"]), "當日候選排名": int(k["當日候選排名"]), "當日候選數": int(k["當日候選數"]),
                     "該月候選數": int(k["該月候選數"]), "狀態": st_,
                     "預定出場日": est_exit(s, t_in) if st_ == HELD else str(cal[xpos].date()),
                     "_t_in": t_in, "_xref": xref, "_t_out": t_out})
    LST = pd.DataFrame(rows).sort_values(["進場日", "當日候選排名"]).reset_index(drop=True)

    # ── 未入選
    bought = set(zip(T["sid"], T["t_in"]))
    fate = {}
    for r_ in lg:
        fate.setdefault((r_["sid"], int(r_["entry_pos"])), r_["reason"])
    rr = []
    for k in E.itertuples():
        if (k.sid, k.entry_pos) in bought:
            continue
        f = fate.get((k.sid, int(k.entry_pos)))
        if f == "in":
            raise SystemExit(f"⛔ log 說進了但 audit 沒有：{k.sid} {k.進場日}")
        if f not in WHY:
            raise SystemExit(f"⛔ 未知去向 {f}")
        s = k.sid; t_in = int(k.entry_pos); xpos = int(k.xpos_H60); stk(s)
        ep = float(opens[s][t_in]); g = float(k.g_H60)
        held = xpos == NC
        rr.append({"進場日": k.進場日, "代號": s, "名稱": stocks["name"].get(s, ""), "市場": mk.get(s, ""),
                   "進場價_還原": ep, "進場價_原始": rawv(s, t_in, "open"),
                   "出場日": "2026-09-24" if held else str(cal[xpos].date()), "出場價_還原": ep * (1 + g),
                   "出場價_原始": rawv(s, NC - 1 if held else xpos, "close"),
                   "出場說明": "資料尾：以 2026-09-24 收盤計" if held else "H60 到期（第 60 根收盤）",
                   "報酬_扣成本_pct": (g - R.COST) * 100, "毛報酬_pct": g * 100,
                   "relvol": float(k.relvol), "當日候選排名": int(k.當日候選排名), "當日候選數": int(k.當日候選數),
                   "該月候選數": int(k.該月候選數), "狀態": "未入選" + ("（H60 未到，以 9/24 收盤計）" if held else ""),
                   "未入選原因": WHY[f], "預定出場日": est_exit(s, t_in) if held else str(cal[xpos].date())})
    for k in X.itertuples():
        rr.append({"進場日": k.進場日, "代號": k.sid, "名稱": stocks["name"].get(k.sid, ""), "市場": mk.get(k.sid, ""),
                   "relvol": float(k.relvol), "狀態": "未入選（引擎排除）",
                   "未入選原因": "引擎排除：H60 出場日缺（非資料尾截斷，例如下市或壞根）", "報酬_扣成本_pct": np.nan})
    REST = pd.DataFrame(rr).sort_values(["進場日", "當日候選排名"]).reset_index(drop=True)
    assert len(LST) + int((REST["狀態"] != "未入選（引擎排除）").sum()) == len(E)

    cols = ["進場日", "代號", "名稱", "市場", "進場價_還原", "進場價_原始", "出場日", "出場價_還原", "出場價_原始", "出場說明",
            "報酬_扣成本_pct", "毛報酬_pct", "relvol", "當日候選排名", "當日候選數", "該月候選數", "狀態", "預定出場日"]
    fmt = LST[cols].copy()
    fmt.to_csv(os.path.join(OUT, F_LIST), index=False, encoding="utf-8-sig", float_format="%.6f")
    REST[cols[:-1] + ["未入選原因", "預定出場日"]].to_csv(os.path.join(OUT, F_REST), index=False, encoding="utf-8-sig", float_format="%.6f")

    write_md(LST, REST, G, SF)
    write_html(LST, REST, G, cal, stk, NC)
    print(f"[完成] 入選 {len(LST)}、未入選 {len(REST)}（其中引擎排除 {len(X)}）｜{time.time() - t00:.0f}s", flush=True)
    for f in (F_LIST, F_REST, F_MD, F_HTML):
        print(f"  {os.path.join(OUT, f)}  {os.path.getsize(os.path.join(OUT, f)):,} bytes")


# ═════════════ 摘要 ═════════════
def monthly(LST, REST):
    R_ = REST[REST["狀態"] != "未入選（引擎排除）"]
    out = []
    for m in sorted(set(LST["進場日"].str[:7]) | set(R_["進場日"].str[:7])):
        a = LST[LST["進場日"].str[:7] == m]["報酬_扣成本_pct"]; b = R_[R_["進場日"].str[:7] == m]["報酬_扣成本_pct"]
        cand = int(pd.concat([LST[LST["進場日"].str[:7] == m]["該月候選數"], R_[R_["進場日"].str[:7] == m]["該月候選數"]]).iloc[0])
        out.append({"月": m, "入選": len(a), "平均": a.mean() if len(a) else np.nan, "勝率": (a > 0).mean() * 100 if len(a) else np.nan,
                    "持有中": int((LST[LST["進場日"].str[:7] == m]["狀態"] == HELD).sum()),
                    "未入選": len(b), "未入選平均": b.mean() if len(b) else np.nan, "候選": cand})
    return pd.DataFrame(out)


def _p(x, d=2):
    return "—" if x is None or not np.isfinite(x) else f"{x:+.{d}f}%"


def overall(LST, REST):
    a = LST["報酬_扣成本_pct"]; R_ = REST[REST["狀態"] != "未入選（引擎排除）"]["報酬_扣成本_pct"]
    ex = LST[LST["狀態"] == "已出場"]["報酬_扣成本_pct"]
    return {"n": len(a), "mean": a.mean(), "med": a.median(), "win": (a > 0).mean() * 100, "best": a.max(), "worst": a.min(),
            "held": int((LST["狀態"] == HELD).sum()), "sf": int(LST["出場說明"].str.startswith("停止交易").sum()),
            "ex_n": len(ex), "ex_mean": ex.mean(), "ex_win": (ex > 0).mean() * 100,
            "rest_n": len(R_), "rest_mean": R_.mean(), "rest_win": (R_ > 0).mean() * 100,
            "rest_x": int((REST["狀態"] == "未入選（引擎排除）").sum()), "codes": LST["代號"].nunique()}


def write_md(LST, REST, G, SF):
    M = monthly(LST, REST); O = overall(LST, REST)
    L = ["# 營量 v1 名單 2025-08～2026-06（描述，⛔ 不判）", "",
         f"產出 {pd.Timestamp.now(tz='Asia/Taipei'):%Y-%m-%d %H:%M}（台北）｜回測線｜裁定 seq263 §二", "",
         f"**全期：入選 {O['n']} 筆（{O['codes']} 檔），平均報酬 {_p(O['mean'])}、中位 {_p(O['med'])}、勝率 {O['win']:.1f}%。**", "",
         f"- 已出場 {O['ex_n']} 筆：平均 {_p(O['ex_mean'])}、勝率 {O['ex_win']:.1f}%",
         f"- {HELD} {O['held']} 筆；停止交易強制出場 {O['sf']} 筆",
         f"- 未入選候選 {O['rest_n']} 筆（照 H60 算）：平均 {_p(O['rest_mean'])}、勝率 {O['rest_win']:.1f}%"
         + (f"；另有引擎排除 {O['rest_x']} 筆（無報酬）" if O["rest_x"] else ""), "",
         "## 每月（依進場月）", "",
         "| 月 | 入選 | 平均 | 勝率 | 未入選 | 候選 |", "|---|---|---|---|---|---|"]
    for r in M.itertuples():
        L.append(f"| {r.月} | {r.入選}{'（持有中 ' + str(r.持有中) + '）' if r.持有中 else ''} | {_p(r.平均)} | "
                 f"{'—' if not np.isfinite(r.勝率) else f'{r.勝率:.0f}%'} | {r.未入選} | {r.候選} |")
    L.append(f"| **全期** | **{O['n']}** | **{_p(O['mean'])}** | **{O['win']:.0f}%** | **{O['rest_n']}** | **{int(M['候選'].sum())}** |")
    L += ["", "## 規則與口徑", "",
          "- 營量 v1 ＝ 219 表 #13：PREREGP1 AND 訊號、20 槽、每日不設上限、依 relvol 大者先（不抽籤）、持有 60 個交易日、無大盤閘、來回成本 0.585%",
          "- 正式版 ＝ T1（資料尾截斷訊號補回）＋ 停止交易強制出場：開（researchT1fix.py，commit 1e7229c101）",
          "- **種子無影響**：relvol 排序不抽籤；取種子 0 的實際成交（引擎 audit）",
          f"- 閘門：本次重跑權益 ＝ resultsT1fix/seeds.csv.gz（c13｜t1｜種子 0）逐位元 ⇒ **{'通過' if G['全過'] else '不過'}**"
          f"（主窗年化 {G['本檔']['cagr'] * 100:+.2f}%／回落 {G['本檔']['mdd'] * 100:+.2f}%，全期成交 {G['本檔']['trades']} 筆）",
          "- 報酬 ＝ 出場價 ÷ 進場價 − 1 − 0.585%（還原價）；進場 ＝ 訊號隔日開盤，出場 ＝ 第 60 根收盤",
          f"- {HELD}：H60 還沒到，以 2026-09-24 收盤計值並**預扣** 0.585%；預定出場日為推估",
          "- 排名 ＝ 當日全部候選（含已持有的）依 relvol 大者先；候選 ＝ 引擎可用的 AND 訊號",
          "- 未入選原因：當日 20 槽全滿／空槽不足（名次在可買數之後）／已持有同一檔",
          "- ⛔ 這是逐筆報酬的描述，不是組合報酬，也不是新回測；不改任何判定、不計 N",
          "- 圖：依使用者指示以網頁交付（單一 HTML、SVG 圖，手機可直接開；摘要表在網頁最上方）", "",
          "## 檔案", "",
          f"- `{F_LIST}`（入選）", f"- `{F_REST}`（未入選）", f"- `{F_HTML}`（K 線圖，入選每筆一張）", ""]
    open(os.path.join(OUT, F_MD), "w", encoding="utf-8").write("\n".join(L))


# ═════════════ HTML ═════════════
CSS = """
:root{color-scheme:light}
body{margin:0;background:#f6f6f4;color:#222;font-family:sans-serif;line-height:1.5}
main{max-width:1080px;margin:0 auto;padding:12px 16px 40px}
h1{font-size:1.3rem;margin:.4em 0}h2{font-size:1.1rem;margin:1.2em 0 .4em}h3{font-size:1.02rem;margin:.2em 4px}
.lead{font-size:1rem;background:#fff;border-left:4px solid #d62728;padding:8px 12px}
table{border-collapse:collapse;width:100%;background:#fff;font-size:.9rem}
th,td{border-bottom:1px solid #e3e3e3;padding:4px 6px;text-align:right;white-space:nowrap}
th:first-child,td:first-child{text-align:left}
.wrap{overflow-x:auto}
.pos{color:#c62828}.neg{color:#2e7d32}
.toc{display:grid;grid-template-columns:repeat(auto-fill,minmax(250px,1fr));gap:2px 12px;font-size:.88rem;background:#fff;padding:8px}
.toc a{color:#1a4fa0;text-decoration:none}
.card{background:#fff;margin:14px 0;padding:6px;border:1px solid #e3e3e3}
.card .meta{font-size:.82rem;color:#555;padding:2px 4px 6px}
.legend{font-size:.85rem;background:#fff;padding:6px 8px;position:sticky;top:0;z-index:2;border-bottom:1px solid #ddd}
.note{font-size:.85rem;color:#555}
.back{font-size:.8rem;float:right}
"""


def _cls(x):
    return "pos" if x > 0 else ("neg" if x < 0 else "")


def write_html(LST, REST, G, cal, stk, NC):
    M = monthly(LST, REST); O = overall(LST, REST)
    H_ = ['<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8">',
          '<meta name="viewport" content="width=device-width,initial-scale=1">',
          "<title>營量 v1 K 線圖</title>", f"<style>{CSS}</style></head><body><main id='top'>",
          "<h1>營量 v1 名單 2025-08～2026-06：K 線＋均線</h1>",
          f"<p class='lead'>入選 <b>{O['n']}</b> 筆（{O['codes']} 檔），平均報酬 <b class='{_cls(O['mean'])}'>{_p(O['mean'])}</b>、"
          f"勝率 <b>{O['win']:.1f}%</b>；已出場 {O['ex_n']} 筆平均 {_p(O['ex_mean'])}；{HELD} {O['held']} 筆。</p>",
          "<p class='note'>⛔ 逐筆描述，不是組合報酬、不是新回測。種子無影響（relvol 排序不抽籤）；閘門 "
          + ("通過" if G["全過"] else "不過") + "。報酬已扣 0.585%。還原價。依使用者指示以網頁交付。</p>",
          "<h2>每月摘要（依進場月）</h2><div class='wrap'><table><tr><th>月</th><th>入選</th><th>平均</th><th>勝率</th><th>未入選</th><th>候選</th></tr>"]
    for r in M.itertuples():
        H_.append(f"<tr><td>{r.月}</td><td>{r.入選}{'（持有 ' + str(r.持有中) + '）' if r.持有中 else ''}</td>"
                  f"<td class='{_cls(r.平均) if np.isfinite(r.平均) else ''}'>{_p(r.平均)}</td>"
                  f"<td>{'—' if not np.isfinite(r.勝率) else f'{r.勝率:.0f}%'}</td><td>{r.未入選}</td><td>{r.候選}</td></tr>")
    H_.append(f"<tr><th>全期</th><th>{O['n']}</th><th class='{_cls(O['mean'])}'>{_p(O['mean'])}</th><th>{O['win']:.0f}%</th>"
              f"<th>{O['rest_n']}</th><th>{int(M['候選'].sum())}</th></tr></table></div>")
    H_.append(f"<p class='note'>未入選候選（照 H60 算）平均 {_p(O['rest_mean'])}、勝率 {O['rest_win']:.1f}%。</p>")
    H_.append("<h2>目錄</h2><div class='toc'>")
    for i, r in LST.iterrows():
        H_.append(f"<a href='#c{i}'>{r['進場日']} {r['代號']} {html.escape(str(r['名稱']))} "
                  f"<span class='{_cls(r['報酬_扣成本_pct'])}'>{r['報酬_扣成本_pct']:+.1f}%</span>{'＊' if r['狀態'] == HELD else ''}</a>")
    H_.append("</div><p class='note'>＊＝持有中（以 9/24 收盤計）</p>")
    H_.append("<h2>K 線圖（依進場日）</h2>" + CS.legend_html())
    for i, r in LST.iterrows():
        s = r["代號"]; st, _ = stk(s)
        df = st.df
        t_in, xref = int(r["_t_in"]), int(r["_xref"])
        i0 = max(0, t_in - 60); i1 = min(NC - 1, xref + 20)
        cf = pd.Series(df["close"].to_numpy(float)).ffill().to_numpy()
        ma = {k: CS.moving_avg(cf, k)[i0:i1 + 1] for k in (5, 20, 60)}
        sl = slice(i0, i1 + 1)
        dates = [str(x.date()) for x in cal[sl]]
        ret = r["報酬_扣成本_pct"]
        held = r["狀態"] == HELD
        xi = min(xref, NC - 1) - i0
        marks = [{"i": t_in - i0, "px": r["進場價_還原"], "kind": "entry", "label": f"進 {r['進場價_還原']:.2f}"},
                 {"i": xi, "px": r["出場價_還原"], "kind": "exit",
                  "label": (f"9/24 收 {r['出場價_還原']:.2f}" if held else f"出 {r['出場價_還原']:.2f}")}]
        title = f"{s} {r['名稱']}｜{r['進場日']}→{HELD if held else r['出場日']}｜{ret:+.2f}%"
        sub = (f"原始價 進 {r['進場價_原始']:.2f}／出 {r['出場價_原始']:.2f}｜relvol {r['relvol']:.1f}（當日第 {r['當日候選排名']}／{r['當日候選數']}）"
               f"｜{r['出場說明']}")
        svg = CS.kline_svg(dates, df["open"].to_numpy(float)[sl], df["high"].to_numpy(float)[sl], df["low"].to_numpy(float)[sl],
                           df["close"].to_numpy(float)[sl], df["volume"].to_numpy(float)[sl] / 1000.0, ma=ma, marks=marks,
                           shade=(t_in - i0, xi), title=title, subtitle=sub, show_title=False)
        H_.append(f"<section class='card' id='c{i}'><a class='back' href='#top'>回目錄</a>"
                  f"<h3>{html.escape(s + ' ' + str(r['名稱']))}｜{r['進場日']}→{HELD if held else r['出場日']}｜"
                  f"<span class='{_cls(ret)}'>{ret:+.2f}%</span></h3><div class='meta'>{html.escape(sub)}</div>{svg}"
                  f"<div class='meta'>{i + 1}／{len(LST)}｜還原價｜量單位：張｜預定出場日 {html.escape(str(r['預定出場日']))}</div></section>")
    H_.append("</main></body></html>")
    open(os.path.join(OUT, F_HTML), "w", encoding="utf-8").write("\n".join(H_))


if __name__ == "__main__":
    main()

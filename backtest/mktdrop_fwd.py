# -*- coding: utf-8 -*-
"""PREREG大盤大跌後買什麼 seq1 前瞻紀錄維護（回測線程式子代理，2026-10-17）：補買進列、收復檢查、每日名單第八節。
依據：backtest/researchMktDrop_v1.py 檔頭 §二～§三（照登錄）；紀錄 backtest/forward/mktdrop/（events.csv、positions.csv）。
⛔ 只描述、不判；⛔ 不是買賣建議；用語「假訊號」。

    補買進列（事件 t 的下一交易日資料到了之後）：
      cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.mktdrop_fwd buy --seq 0 \
          --cands backtest/forward/mktdrop/candidates_20261015.csv [--sha SHA] [--dry]
    每日（run_daily_list.sh：daily_list 產檔之後、複製到信箱之前；⛔ 失敗只記 log、不影響 daily）：
      ... -m backtest.mktdrop_fwd daily --asof <資料日> --sha <main sha> --md backtest/resultsDaily/daily_<資料日>.md [--nowrite] [--fwd DIR]
      ＝ researchMktDrop_v1.fwd_judge_and_record(資料日, write)（同 --judge 資料日 --write）＋ 待買事件補買進列（候選檔在才補）
        ＋ 收復檢查 ＋ 名單末尾加「## 八、（內部）大盤大跌前瞻」（⛔ 前面各節逐位元不動，只在檔尾加；已有第八節 ⇒ 換掉那一節）

讀法（執行者補；第一次寫入之前寫死，2026-10-17 台北）：
 買進：事件日 t 在個股日曆（data/meta/calendar_twse.csv）的下一交易日 e 開盤；買進價欄 ＝ e 未還原開盤（紀錄用）
   買不到 ＝ e 沒成交（未還原收盤缺／≤0）∨ 開盤缺／≤0 ∨ 開盤漲停鎖死（tradability.one 的 up_o ∧ 未還原最低 ＝ 開盤，同 researchDumb_check）
            ∨ e 是壞根（researchBARR.bad_part ∪ adj 減資／面額，同 forward/mktdrop_cands.py）；
   ETF（A、B）只看有成交 ∧ 開盤有效（同 researchMktDrop.etf_pack）
   買不到的也寫一列（狀態「買不到」、備註原因）⇒ 比例照報；F 0 檔 ⇒ 一列「不進場（0 檔）」
   C+（C 裡最近一期營收年增 > 0）＝ 協調者加的描述格，v1 沒有、不入判
 收復檢查：加權收盤（公開庫 market_index.csv）≥ 事件前一日收盤的第一天 D（D ＞ t、D ≤ 資料日）⇒ events.csv 收復日 ＝ D；
   每檔賣 ＝ D 之後第一根可賣開盤（有成交 ∧ 開盤有效 ∧ 非開盤跌停鎖死〔dn_o ∧ 未還原最高 ＝ 開盤〕；鎖跌停順延；ETF 只看開盤有效）；
   買進根之後出現壞根 k、且 k 不晚於規則賣出根 ⇒ k 之前最後一根有成交的收盤強制賣（同 researchMktDrop.exits_core：規則賣出要 S ＜ kb）；
   報酬欄 ＝ 還原價（賣價 ÷ 買進根還原開盤）− 1 再扣來回成本（個股 0.585%、ETF 0.385%）；出場價欄 ＝ 未還原價
   全籃都不在持有中（已出場／買不到／不進場）⇒ events.csv 賣出日 ＝ 最後賣出日、狀態「已出場」
   下市（之後不再成交）：程式不自動判；資料日前 5 個交易日都沒成交 ⇒ 第八節提醒
 帳面（第八節）：持有中每檔 還原收盤（資料日；當天沒成交用最近一根）÷ 買進根還原開盤 − 1，候選等權平均（未扣成本；另列扣來回成本）
 改既有列：只動吻合「恰好 1 列」的那一列的指定欄；非空欄只准改「狀態／備註」（其他欄非空且不同 ⇒ 拒絕）；
   以原始文字逐行改、寫暫存檔再 os.replace ⇒ 其他列逐位元不變（寫完再讀回比對）
── 2026-10-17 加（回測線程式子代理；只加、不改既有輸出）──
 自動候選名單：daily 判到「事件」且要寫 ⇒ 當天呼叫 backtest.mktdrop_cands.make_candidates(資料日, sha, md＝當天名單檔) 寫 candidates_<日>.csv
   （A、B、C、C+、E、F 同 forward/mktdrop_cands.py；F ＝ 名單第二節營量 v1 已達成；候選檔已在 ⇒ 不重產；⛔ 失敗只記 log、第八節照出）
 F8top3（研究紀錄、未驗證、不入判）：候選檔「候選」欄 F8top3 的 3 列（C+ 內 F6 名次＋F7 名次前 3）⇒ 補買進列時一併寫 positions（候選 F8top3）；
   收復／出場同其他列；第八節既有各行只算 A～F（F8top3 不併入帳面、買不到、久未成交），另加「F8 前 3」行：事件／待買 ⇒ 名單；持有中 ⇒ 帳面；已出場 ⇒ 扣成本報酬
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import os
import sys

import numpy as np
import pandas as pd

from backtest import data as D
from backtest import tradability as TR
from backtest import researchBARR as BARR
from backtest import researchMktDrop_v1 as RM

ETFS = ("0050", "00631L")
CANDS_IN = ("A", "B", "C", "C+", "D", "E", "F")
F8TAG = "F8top3"                                                   # 2026-10-17 加：研究紀錄、未驗證、不入判
BUY_IN = CANDS_IN + (F8TAG,)
F8NOTE = "研究紀錄、未驗證"
EDITABLE = ("狀態", "備註")
SEC_TITLE = "## 八、（內部）大盤大跌前瞻（研究紀錄、未驗證；不推 LINE）"
SEC_NOTE = ("PREREG大盤大跌後買什麼 seq1 的前瞻紀錄（backtest/forward/mktdrop/）：看過初測才登錄、最多暫定；事件累計 ≥ 10 次才判一次；"
            "⛔ 不是買賣建議。給回測線核對用，情報要不要推另議。")


def ddir(sha):
    p = os.path.expanduser(f"~/h2data/{sha}/data")
    if not os.path.isdir(os.path.join(p, "stocks")):
        raise SystemExit(f"⛔ 沒有 archive：{p}（先跑 run_daily_list.sh 或 git archive）")
    return p


def cost_of(sid):
    return RM.COST_ETF if sid in ETFS else RM.COST_STK


# ═════════════ 紀錄檔：讀、安全改一列 ═════════════
def read_rows(fn):
    p = os.path.join(RM.FWD, fn)
    with open(p, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.reader(f))
    return [dict(zip(rows[0], r)) for r in rows[1:]]


def _fmt(v):
    if v is None:
        return ""
    if isinstance(v, (float, np.floating)):
        return "" if not np.isfinite(v) else repr(float(v))
    if isinstance(v, pd.Timestamp):
        return str(v.date())
    return str(v)


def fwd_update(fn, cols, match, upd):
    """events.csv／positions.csv：吻合 match（欄 ⇒ 值，全等）的列【恰好 1 列】⇒ 改 upd 指定的欄。⇒ True＝有改、False＝本來就一樣。
    非空欄只准改 EDITABLE（狀態／備註）；以原始文字逐行處理，其他列逐位元不變（寫完讀回比對）。"""
    p = os.path.join(RM.FWD, fn)
    b = open(p, "rb").read()
    bom = b.startswith(b"\xef\xbb\xbf")
    txt = b.decode("utf-8-sig")
    lines = txt.splitlines(keepends=True)
    head = next(csv.reader([lines[0]]))
    if head != cols:
        raise SystemExit(f"⛔ {p} 表頭不同：{head}")
    bad = set(upd) - set(cols)
    if bad:
        raise SystemExit(f"⛔ 多出欄位 {bad}")
    hit = []
    for i in range(1, len(lines)):
        if not lines[i].strip():
            continue
        r = next(csv.reader([lines[i]]))
        if all(r[cols.index(k)] == _fmt(v) for k, v in match.items()):
            hit.append((i, r))
    if len(hit) != 1:
        raise SystemExit(f"⛔ {fn} 吻合 {len(hit)} 列（要恰好 1 列）：{match}")
    i, r = hit[0]
    new = list(r)
    for k, v in upd.items():
        j = cols.index(k); v = _fmt(v)
        if new[j] not in ("", v) and k not in EDITABLE:
            raise SystemExit(f"⛔ {fn} 第 {i} 列「{k}」已有值 {new[j]!r}，不改成 {v!r}")
        new[j] = v
    if new == r:
        return False
    term = lines[i][len(lines[i].rstrip("\r\n")):] or "\r\n"
    buf = io.StringIO(); csv.writer(buf, lineterminator=term).writerow(new)
    out = list(lines); out[i] = buf.getvalue()
    tmp = p + ".tmp"
    with open(tmp, "wb") as f:
        f.write((b"\xef\xbb\xbf" if bom else b"") + "".join(out).encode("utf-8"))
    os.replace(tmp, p)
    back = open(p, "rb").read().decode("utf-8-sig").splitlines(keepends=True)
    if len(back) != len(lines) or any(back[k] != lines[k] for k in range(len(lines)) if k != i):
        raise SystemExit(f"⛔ {p} 寫回比對失敗：其他列有變")
    return True


# ═════════════ 價格（一檔） ═════════════
def one(sid, mk, cal, DATA):
    """⇒ 日曆長陣列：未還原 o/h/l/c、還原 ao/ac、trd、upl（開盤漲停鎖死）、dnl（開盤跌停鎖死）、bad（壞根）。"""
    D.DATA = DATA
    etf = sid in ETFS
    st = D.load_stock(sid, mk, cal)
    n = len(cal)
    if st is None:
        z = np.full(n, np.nan); f = np.zeros(n, bool)
        return {"ro": z, "rh": z, "rl": z, "rc": z, "ao": z, "ac": z, "trd": f, "upl": f, "dnl": f, "bad": f}
    raw = pd.read_csv(os.path.join(DATA, "stocks", f"{sid}.csv"), dtype={"date": str}, usecols=["date", "open", "high", "low", "close"])
    raw["date"] = pd.to_datetime(raw["date"]); raw = raw.drop_duplicates("date").set_index("date").reindex(cal)
    ro, rh, rl, rc = (np.array(pd.to_numeric(raw[k], errors="coerce"), dtype=float) for k in ("open", "high", "low", "close"))
    for a_ in (ro, rh, rl, rc):
        a_[~(a_ > 0)] = np.nan
    tb = TR.one(sid, cal)
    trd = np.asarray(tb["trd"], bool)
    if etf:
        upl = np.zeros(n, bool); dnl = np.zeros(n, bool); bad = np.zeros(n, bool)
    else:
        with np.errstate(invalid="ignore"):
            upl = np.asarray(tb["up_o"], bool) & (rl == ro); dnl = np.asarray(tb["dn_o"], bool) & (rh == ro)
        bad = BARR.bad_part(sid, DATA, cal).copy()
        D.DATA = DATA
        adj = D.load_adj(sid)
        if adj is not None and len(adj) and "event" in adj:
            for d, e in zip(adj["date"], adj["event"].astype(str)):
                if e in ("reduce", "parvalue"):
                    k = int(cal.searchsorted(d))
                    if k < n:
                        bad[k] = True
    return {"ro": ro, "rh": rh, "rl": rl, "rc": rc, "ao": st.df["open"].to_numpy(float), "ac": st.df["close"].to_numpy(float),
            "trd": trd, "upl": upl, "dnl": dnl, "bad": bad}


def meta(DATA):
    s = pd.read_csv(os.path.join(DATA, "meta", "stocks.csv"), dtype=str).drop_duplicates("stock_id", keep="last").set_index("stock_id")
    return s["market"].to_dict(), s["name"].to_dict()


# ═════════════ 一、補買進列 ═════════════
def fill_buys(seq, cands, sha, write=True, log=print):
    DATA = ddir(sha); D.DATA = DATA; cal = D.load_calendar()
    evs = [r for r in read_rows("events.csv") if r["序號"] == str(seq)]
    if len(evs) != 1:
        raise SystemExit(f"⛔ events.csv 序號 {seq} 有 {len(evs)} 列")
    ev = evs[0]
    if ev["狀態"] != "待買":
        raise SystemExit(f"⛔ 序號 {seq} 狀態是「{ev['狀態']}」不是「待買」")
    if any(r["序號"] == str(seq) for r in read_rows("positions.csv")):
        raise SystemExit(f"⛔ positions.csv 已有序號 {seq} 的列（只追加、不重寫）")
    t = pd.Timestamp(ev["事件日"]); pt = int(cal.searchsorted(t))
    if pt >= len(cal) or cal[pt] != t:
        raise SystemExit(f"⛔ 事件日 {t.date()} 不在個股日曆")
    e = pt + 1
    if e >= len(cal):
        return {"狀態": "資料未到", "事件日": str(t.date()), "日曆尾": str(cal[-1].date())}
    bd = cal[e]
    C = pd.read_csv(cands, dtype=str, encoding="utf-8-sig").fillna("")
    C = C[C["候選"].isin(BUY_IN)]
    mk, nm = meta(DATA)
    now = RM.now_tpe(); rows = []; summ = {}
    tag0 = "第 0 筆描述、不入判" if int(seq) == 0 else ""
    for _, c in C.iterrows():
        cd, sid = c["候選"], c["代號"].strip()
        S = summ.setdefault(cd, {"選出": 0, "買到": 0, "買不到": [], "帳面": []})
        base = {"序號": seq, "事件日": str(t.date()), "候選": cd, "代號": sid, "名稱": c["名稱"] or nm.get(sid, ""), "出場條件": RM.FWD_EXIT, "寫入時間": now}
        if not sid:
            rows.append({**base, "狀態": "不進場（0 檔）", "備註": "；".join(x for x in (tag0, c["備註"]) if x)}); continue
        S["選出"] += 1
        X = one(sid, mk.get(sid, "twse"), cal, DATA)
        why = []
        if not X["trd"][e]:
            why.append("隔天沒成交")
        elif not np.isfinite(X["ro"][e]):
            why.append("隔天開盤缺")
        if X["upl"][e]:
            why.append("開盤漲停鎖死")
        if X["bad"][e]:
            why.append("隔天是壞根")
        note = [x for x in (tag0, "C+ ＝ C 裡最近一期營收年增 > 0（描述格，v1 沒有、不入判）" if cd == "C+" else "",
                            "正2 含槓桿效果" if cd == "B" else "",
                            "F8top3 ＝ C+ 內 F6 名次＋F7 名次前 3（研究紀錄、未驗證、不入判）" if cd == F8TAG else "") if x]
        if why:
            S["買不到"].append(f"{sid}（{'、'.join(why)}）")
            rows.append({**base, "狀態": "買不到", "備註": "；".join(note + [f"買不到：{'、'.join(why)}（{bd.date()}）"])})
            continue
        S["買到"] += 1
        mark = float(X["rc"][e] / X["ro"][e] - 1.0)
        S["帳面"].append(mark)
        rows.append({**base, "買進日": str(bd.date()), "買進價": float(X["ro"][e]), "狀態": "持有中",
                     "備註": "；".join(note + [f"買進價＝{bd.date()} 未還原開盤"])})
    out = {"事件日": str(t.date()), "買進日": str(bd.date()), "sha": sha,
           "候選": {cd: {"選出": v["選出"], "買到": v["買到"], "買不到檔數": len(v["買不到"]), "買不到": v["買不到"],
                       "帳面（買進日收盤÷開盤−1，等權、未扣成本）": (float(np.mean(v["帳面"])) if v["帳面"] else None),
                       "帳面扣來回成本": ((1 + float(np.mean(v["帳面"]))) * (1 - (RM.COST_ETF if cd in ("A", "B") else RM.COST_STK)) - 1 if v["帳面"] else None),
                       **({"代號": [r_["代號"] for r_ in rows if r_["候選"] == cd]} if cd == F8TAG else {})}
                    for cd, v in summ.items()}}
    if write:
        RM.fwd_append_positions(rows)
        fwd_update("events.csv", RM.FWD_EV_COLS, {"序號": seq, "事件日": str(t.date())}, {"買進日": str(bd.date()), "狀態": "持有中"})
        out["寫入"] = f"positions.csv ＋{len(rows)} 列；events.csv 序號 {seq} 買進日 {bd.date()}、狀態 持有中"
    else:
        out["寫入"] = "（dry：沒寫）"
    log(json.dumps(out, ensure_ascii=False, default=str))
    return out


# ═════════════ 二、收復檢查（每日） ═════════════
def recovery(asof, sha, write=True, log=print):
    """⇒ list（每個持有中／待買事件一個 dict）；write ⇒ 補 events 收復日／賣出日／狀態、positions 出場欄。"""
    asof = pd.Timestamp(asof)
    _, idx = RM.read_index(sha)
    ix = idx[idx["date"] <= asof].reset_index(drop=True)
    DATA = ddir(sha); D.DATA = DATA; cal = D.load_calendar()
    na = int(cal.searchsorted(asof, "right")) - 1                     # 資料日在日曆的位置（≤ asof 的最後一天）
    mk, _nm = meta(DATA)
    res = []
    for ev in read_rows("events.csv"):
        if ev["狀態"] == "已出場" and ev["賣出日"] == str(asof.date()):      # 同一資料日重產（main 換 sha）⇒ 第八節照樣列出場那一行
            R = {"序號": ev["序號"], "事件日": ev["事件日"], "入判": ev["入判"], "收復日": ev["收復日"], "狀態": "已出場", "候選": {}}
            for p in read_rows("positions.csv"):
                if p["序號"] == ev["序號"] and p["狀態"] == "已出場":
                    R["候選"].setdefault(p["候選"], {"報酬": []})["報酬"].append(float(p["報酬"]))
                if p["序號"] == ev["序號"] and p["候選"] == F8TAG:
                    R.setdefault("F8明細", []).append((p["代號"], p["名稱"], p["狀態"], float(p["報酬"]) if p["狀態"] == "已出場" else None))
            res.append(R)
            continue
        if ev["狀態"] not in ("待買", "持有中"):
            continue
        seq = ev["序號"]; t = pd.Timestamp(ev["事件日"]); tgt = float(ev["前一日收盤（收復目標）"])
        if t > asof:
            continue
        aft = ix[ix["date"] > t]
        hit = aft[aft["close"] >= tgt]
        Dd = hit["date"].iloc[0] if len(hit) else None
        R = {"序號": seq, "事件日": str(t.date()), "入判": ev["入判"], "收復目標": tgt, "指數資料日": str(ix["date"].iloc[-1].date()),
             "指數收盤": float(ix["close"].iloc[-1]), "收復日": (str(Dd.date()) if Dd is not None else None), "狀態": ev["狀態"], "候選": {}}
        res.append(R)
        if Dd is not None and write and not ev["收復日"]:
            fwd_update("events.csv", RM.FWD_EV_COLS, {"序號": seq, "事件日": str(t.date())}, {"收復日": str(Dd.date())})
        if ev["狀態"] == "待買":
            continue
        pD = int(cal.searchsorted(Dd)) if Dd is not None else None
        P = [p for p in read_rows("positions.csv") if p["序號"] == seq]
        for p in P:
            cd = p["候選"]
            S = R["候選"].setdefault(cd, {"持有": 0, "已出場": 0, "買不到": 0, "帳面": [], "報酬": [], "賣出日": [], "久未成交": []})
            f8m = (lambda st_, v_: R.setdefault("F8明細", []).append((p["代號"], p["名稱"], st_, v_))) if cd == F8TAG else (lambda st_, v_: None)
            if p["狀態"] == "買不到":
                S["買不到"] += 1; f8m("買不到", None); continue
            if p["狀態"] == "已出場":
                S["已出場"] += 1; S["報酬"].append(float(p["報酬"])); S["賣出日"].append(p["出場日"]); f8m("已出場", float(p["報酬"])); continue
            if p["狀態"] != "持有中":
                continue
            sid = p["代號"]; e = int(cal.searchsorted(pd.Timestamp(p["買進日"])))
            if e > na:
                continue                                              # 買進日在資料日之後（重產舊資料日）
            X = one(sid, mk.get(sid, "twse"), cal, DATA)
            tr = np.flatnonzero(X["trd"][: na + 1]); tr = tr[tr >= e]
            kb = next((int(k) for k in tr if k > e and X["bad"][k]), None)
            ks = None
            if pD is not None:
                for k in range(pD + 1, na + 1):
                    if X["trd"][k] and np.isfinite(X["ro"][k]) and np.isfinite(X["ao"][k]) and not X["dnl"][k]:
                        ks = k; break
            sell = None
            if kb is not None and (ks is None or kb <= ks):
                kp = int(tr[tr < kb][-1])
                sell = (kp, float(X["rc"][kp]), float(X["ac"][kp]), "壞根前一根收盤強制賣")
            elif ks is not None:
                sell = (ks, float(X["ro"][ks]), float(X["ao"][ks]), "主（收復後隔天開盤）")
            if sell is None:
                kl = int(tr[-1])
                S["持有"] += 1; S["帳面"].append(float(X["ac"][kl] / X["ao"][e] - 1.0)); f8m("持有中", S["帳面"][-1])
                if na - kl >= 5:
                    S["久未成交"].append(f"{sid}（最後成交 {cal[kl].date()}）")
                continue
            k, px, apx, kind = sell
            g = apx / float(X["ao"][e]) - 1.0; net = (1 + g) * (1 - cost_of(sid)) - 1
            S["已出場"] += 1; S["報酬"].append(net); S["賣出日"].append(str(cal[k].date())); f8m("已出場", net)
            if write:
                fwd_update("positions.csv", RM.FWD_POS_COLS, {"序號": seq, "候選": cd, "代號": sid},
                           {"出場日": str(cal[k].date()), "出場價": px, "出場種類": kind, "報酬": net, "狀態": "已出場",
                            "備註": (p["備註"] + "；" if p["備註"] else "") + f"出場補記 {RM.now_tpe()}：還原價毛 {g:+.4%}、扣來回成本 {cost_of(sid):.3%}"})
        if write and P and not any(R["候選"][c]["持有"] for c in R["候選"]):
            sds = [d for c in R["候選"] for d in R["候選"][c]["賣出日"]]
            if sds:
                fwd_update("events.csv", RM.FWD_EV_COLS, {"序號": seq, "事件日": str(t.date())}, {"賣出日": max(sds), "狀態": "已出場"})
                R["狀態"] = "已出場"
    return res


# ═════════════ 三、名單第八節 ═════════════
def _cands_str(R, key, cost=False):
    out = []
    for cd in CANDS_IN:
        S = R["候選"].get(cd)
        if not S or not S[key]:
            continue
        m = float(np.mean(S[key]))
        if cost:
            m = (1 + m) * (1 - (RM.COST_ETF if cd in ("A", "B") else RM.COST_STK)) - 1
        nm = {"A": "A 0050", "B": "B 00631L"}.get(cd, f"{cd} {len(S[key])} 檔")
        out.append(f"{nm} {m:+.2%}")
    return "｜".join(out)


def _f8_pick_line(cf):
    """候選檔的 F8top3 列 ⇒ 「F8 前 3：…」一行（沒有 ⇒ 空）。"""
    try:
        C = pd.read_csv(cf, dtype=str, encoding="utf-8-sig").fillna("")
    except Exception:                                              # noqa: BLE001  讀不了就不列（候選檔另有檢查）
        return []
    C = C[C["候選"] == F8TAG]
    if not len(C):
        return []
    return [f"  - F8 前 3：{'、'.join(f'{s} {n}' for s, n in zip(C['代號'], C['名稱']))}（C+ 內 F6 名次＋F7 名次；{F8NOTE}）"]


def _f8_line(R):
    """recovery 收的 F8top3 明細 ⇒ 一行：持有中帳面（未扣成本）／已出場扣成本報酬／買不到。"""
    it = R.get("F8明細")
    if not it:
        return []
    parts = []
    for s, n, st_, v in it:
        if st_ == "持有中":
            parts.append(f"{s} {n} 帳面 {v:+.2%}")
        elif st_ == "已出場":
            parts.append(f"{s} {n} 已出場 {v:+.2%}（扣成本）")
        else:
            parts.append(f"{s} {n} {st_}")
    hv = [v for _, _, st_, v in it if st_ == "持有中"]
    xv = [v for _, _, st_, v in it if st_ == "已出場"]
    tail = (f"｜持有中等權帳面 {np.mean(hv):+.2%}（未扣成本）" if hv else "") + (f"｜已出場等權 {np.mean(xv):+.2%}（扣成本）" if xv else "")
    return [f"  - F8 前 3（C+ 內 F6 名次＋F7 名次；{F8NOTE}）：{'、'.join(parts)}{tail}"]


def section(J, RS, cands_dir=None):
    L = [SEC_TITLE, "", SEC_NOTE, ""]
    st = J.get("狀態")
    if st == "事件":
        L.append(f"- 今天加權跌 {abs(J['指數報酬']):.2%}，達大跌事件（研究紀錄、未驗證）")
        L.append(f"  - 收盤 {J['收盤']:,.2f}、前一日 {J['前一日收盤']:,.2f}；門檻 {J['門檻']:+.2%}（2005 起日報酬第 2 百分位、前 20 日內無別的）；"
                 f"照登錄明天開盤買候選、加權收盤 ≥ {J['前一日收盤']:,.2f} 後隔天開盤賣（⛔ 不設天數）")
    elif st == "持有中又遇事件":
        L.append(f"- 今天加權跌 {abs(J['指數報酬']):.2%}，達大跌門檻（{J['門檻']:+.2%}），但上一個事件還在持有中 ⇒ 照登錄不加碼（研究紀錄）")
    elif st == "同波段（前 20 日內已有）":
        L.append(f"- 今天加權 {J['指數報酬']:+.2%}，達大跌門檻（{J['門檻']:+.2%}），但前 20 個交易日內已有 ⇒ 不算新事件")
    elif st == "非事件":
        L.append(f"- 今天加權 {J['指數報酬']:+.2%}（收盤 {J['收盤']:,.2f}；大跌門檻 {J['門檻']:+.2%}），未達大跌事件")
    else:
        L.append(f"- 加權指數資料未到（指數資料尾 {J.get('指數資料尾')}），今天沒判")
    for R in RS:
        tg = f"序號 {R['序號']}" + ("，第 0 筆描述、不入判" if R["序號"] == "0" else "")
        if R["狀態"] == "待買":
            ok = cands_dir and os.path.exists(os.path.join(cands_dir, f"candidates_{R['事件日'].replace('-', '')}.csv"))
            L.append(f"- {R['事件日']} 事件（{tg}）待買：" + ("候選名單在，買進日資料到了就補" if ok else "候選名單還沒產（forward/mktdrop_cands.py 要另跑）"))
            if ok:
                L += _f8_pick_line(os.path.join(cands_dir, f"candidates_{R['事件日'].replace('-', '')}.csv"))
            if J.get("候選錯誤") and R["事件日"] == J.get("日期"):
                L.append(f"  - ⚠ 候選名單自動產生失敗（見 backtest/resultsDaily/mktdrop.log）：{J['候選錯誤']}")
            continue
        if R["狀態"] == "已出場":
            L.append(f"- {R['事件日']} 事件（{tg}）已出場（收復日 {R['收復日']}）：扣成本報酬 " + (_cands_str(R, "報酬") or "—"))
            L += _f8_line(R)
            continue
        gap = R["收復目標"] / R["指數收盤"] - 1
        L.append(f"- 持有中：{R['事件日']} 事件（{tg}）｜收復目標 加權收盤 ≥ {R['收復目標']:,.2f}，"
                 + (f"{R['收復日']} 已收復 ⇒ 下一交易日開盤賣（研究紀錄）" if R["收復日"] else f"{R['指數資料日']} 收盤 {R['指數收盤']:,.2f}（還差 {gap:+.2%}）"))
        bk = _cands_str(R, "帳面")
        if bk:
            L.append(f"  - 帳面（自買進日開盤、還原價、等權、未扣成本）：{bk}")
        ex = _cands_str(R, "報酬")
        if ex:
            L.append(f"  - 已出場的（扣成本）：{ex}")
        L += _f8_line(R)
        nb = sum(S["買不到"] for c_, S in R["候選"].items() if c_ != F8TAG)
        if nb:
            L.append(f"  - 買不到已剔除：{nb} 檔（明細 positions.csv）")
        stale = [x for c_, S in R["候選"].items() if c_ != F8TAG for x in S["久未成交"]]
        if stale:
            L.append(f"  - ⚠ 近 5 個交易日沒成交（可能停牌／下市，人工看）：{'、'.join(stale)}")
    return L + [""]


def put_section(md, L):
    """名單檔尾加第八節；已有 ⇒ 換掉那一節。⇒ 前面各節逐位元不動（檢查）。"""
    old = open(md, encoding="utf-8").read()
    k = old.find("\n" + SEC_TITLE)                                 # 名單末尾 "…\n" ＋ "\n## 八、…"（空一行再接本節，同 daily_list 各節）
    base = old[:k] if k >= 0 else old
    if base and not base.endswith("\n"):
        base += "\n"
    new = base + "\n" + "\n".join(L)
    if not (new.startswith(old) if k < 0 else new.startswith(old[:k])):
        raise SystemExit("⛔ 第八節以前的內容有變")
    tmp = md + ".tmp"
    open(tmp, "w", encoding="utf-8").write(new)
    os.replace(tmp, md)
    return len(base)


def daily(a):
    if a.fwd:
        RM.FWD = a.fwd
    write = not a.nowrite
    J = RM.fwd_judge_and_record(a.asof, write)                    # ＝ researchMktDrop_v1 --judge <資料日> [--write]
    J.pop("持有狀態", None)
    cand = None
    if write and J.get("狀態") == "事件" and J.get("日期") == str(pd.Timestamp(a.asof).date()):   # 2026-10-17 加：事件當天自動產候選名單
        cf = os.path.join(RM.FWD, f"candidates_{J['日期'].replace('-', '')}.csv")
        if os.path.exists(cf):
            cand = "候選檔已在、不重產"
        else:
            try:
                from backtest import mktdrop_cands as MC
                CJ = MC.make_candidates(J["日期"], a.sha, md=a.md, fsha=getattr(a, "fsha", None), out=cf, log=print)
                cand = f"候選名單 C {CJ['C 檔數']}、C+ {CJ['C+ 檔數']}、E {CJ['E 檔數']}、F {len(CJ['F'])}、F8 前 3 {'、'.join(CJ['F8前3']) or '無'}"
            except BaseException as ex:                             # noqa: BLE001  ⛔ 失敗只記 log、第八節照出（含 SystemExit）
                import traceback
                traceback.print_exc()
                J["候選錯誤"] = f"{type(ex).__name__}: {ex}"[:300]
                cand = "候選名單產生失敗"
    bought = []
    for ev in read_rows("events.csv"):                            # 待買事件：候選檔在 ∧ 買進日資料到 ⇒ 補買進列
        cf = os.path.join(RM.FWD, f"candidates_{ev['事件日'].replace('-', '')}.csv")
        if ev["狀態"] == "待買" and write and os.path.exists(cf) and pd.Timestamp(ev["事件日"]) < pd.Timestamp(a.asof):
            bought.append(fill_buys(ev["序號"], cf, a.sha, write=True, log=lambda m: None))
    RS = recovery(a.asof, a.sha, write)
    L = section(J, RS, RM.FWD)
    if a.md:
        put_section(a.md, L)
    print("\n".join(L))
    st = "；".join(f"序號 {R['序號']} {R['狀態']}" + (f" 收復 {R['收復日']}" if R["收復日"] else "") for R in RS) or "無持有中事件"
    print(f"判定 {a.asof}：{J.get('狀態')}{'（' + J['寫入'] + '）' if J.get('寫入') else ''}｜{st}"
          + (f"｜{cand}" if cand else "")
          + (f"｜補買進 {len(bought)} 件" if bought else "") + ("｜第八節已加" if a.md else "") + ("｜nowrite" if a.nowrite else ""))


def main():
    ap = argparse.ArgumentParser()
    sp = ap.add_subparsers(dest="cmd", required=True)
    b = sp.add_parser("buy"); b.add_argument("--seq", required=True); b.add_argument("--cands", required=True)
    b.add_argument("--sha", default=None); b.add_argument("--dry", action="store_true"); b.add_argument("--fwd", default=None)
    d = sp.add_parser("daily"); d.add_argument("--asof", required=True); d.add_argument("--sha", required=True); d.add_argument("--md", default=None)
    d.add_argument("--nowrite", action="store_true"); d.add_argument("--fwd", default=None, help="測試用：紀錄資料夾改到別處")
    d.add_argument("--fsha", default=None, help="F8 財報／法人／融資／集保的 sha（預設 ＝ --sha；測試重現用）")
    a = ap.parse_args()
    if a.cmd == "buy":
        if a.fwd:
            RM.FWD = a.fwd
        sha = a.sha or RM.read_index()[0]
        fill_buys(a.seq, a.cands, sha, write=not a.dry)
    else:
        daily(a)


if __name__ == "__main__":
    main()

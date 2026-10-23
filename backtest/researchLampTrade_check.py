# -*- coding: utf-8 -*-
"""照接近燈買賣描述表【獨立對帳】——回測線計算子代理。⛔ 只讀結果夾（只寫 resultsLampTrade/check.json、check.log）。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchLampTrade_check

另一條路（⛔ 不用本線面板、不 import researchLampTrade）：
 K1 5 格重算：原始價 data/stocks/<代號>.csv × data/adj 還原因子（含 reduce、parvalue；日期 d 的倍數 ＝ d 之後第一個事件的 cum_factor）；
    交易日曆 ＝ market_tri.csv 日期；進場／燈號出場 ＝ 燈號月下一個月起第一個該股有成交（開盤 ＞0、量 ＞0）的日子開盤；
    抱 H ＝ 日曆上進場日算第 1 日的第 H 日收盤；大盤 ＝ 前一交易日收盤（開盤進出）／當日收盤（收盤出場）。
    比 R、大盤、超額、格內天花板（相對差 ＜ 1e−6 或絕對差 ＜ 1e−6）。⚠ 截斷格：截斷值以壞根前一根收盤重算；接續值 ＝ 原始×adj 直接算到出場（adj 已含減資因子）。
 K2 全 465 格留空原因用月份字面重推（NA、出場月 ≤ 進場月、出場月超出資料尾、e＋H−1 超出資料尾）⇒ 與 table.csv 逐格相同。
 K3 表頭警語、1503／1513 高點月（另以原始×adj 找 2021-05～2024-12 最高收盤月）。
"""
from __future__ import annotations

import io
import json
import os
import subprocess

import numpy as np
import pandas as pd

os.chdir(os.path.expanduser("~/tw-p17"))
OUT = "backtest/resultsLampTrade"
SHA = json.load(open(os.path.join(OUT, "main.json"), encoding="utf-8"))["sha"]
COST = 0.004425
WARN = "燈號日期是看過大漲之後從新聞挑的、樣本都是贏家 ⇒ 只描述，⛔ 不能當規則證據、不改任何規則"
LOGS = []


def say(s):
    print(s, flush=True); LOGS.append(s)


def gshow(p):
    t = subprocess.run(["git", "show", f"{SHA}:{p}"], capture_output=True)
    return t.stdout if t.returncode == 0 else None


TRI = pd.read_csv(io.BytesIO(gshow("data/history/market_tri.csv")))
TRI["date"] = pd.to_datetime(TRI["date"]); TRI = TRI.set_index("date")["close"].sort_index()
DAYS = TRI.index


def stock(sid):
    S = pd.read_csv(io.BytesIO(gshow(f"data/stocks/{sid}.csv")), dtype={"date": str})
    S["date"] = pd.to_datetime(S["date"])
    for c in ("open", "close", "volume"):
        S[c] = pd.to_numeric(S[c].astype(str).str.replace(",", ""), errors="coerce")
    S = S.drop_duplicates("date", keep="last").set_index("date").sort_index()
    A = pd.read_csv(io.BytesIO(gshow(f"data/adj/{sid}.csv")))
    A["date"] = pd.to_datetime(A["date"]); A = A.sort_values("date")
    ad = A["date"].to_numpy(); cf = A["cum_factor"].to_numpy(float)

    def mult(d):
        k = np.searchsorted(ad, np.datetime64(d), "right")
        return float(cf[k]) if k < len(cf) else 1.0
    S["m"] = [mult(d) for d in S.index]
    S["ao"] = S["open"] * S["m"]; S["ac"] = S["close"] * S["m"]
    S["ok"] = (S["open"] > 0) & (S["volume"] > 0)
    return S, A


def first_open(S, ym):
    d0 = (pd.Period(ym, "M") + 1).to_timestamp()
    q = S[(S.index >= d0) & S["ok"]]
    return q.index[0]


def prev_day(d):
    return DAYS[DAYS.searchsorted(d) - 1]


def cell(seg, sid, L, X, LP, trunc_before=None):
    S, A = stock(sid)
    r = LP[(LP["段"] == seg) & (LP["代號"] == sid)].iloc[0]
    e = first_open(S, r[L]); P0 = S.at[e, "ao"]; t0 = TRI[prev_day(e)]
    if X.startswith("E"):
        x = first_open(S, r[X]); kind = "open"
    else:
        x = DAYS[DAYS.searchsorted(e) + int(X[1:]) - 1]; kind = "close"
    out = {}
    for tag, xx, kk in (("main", (prev_day(trunc_before) if trunc_before is not None else x), ("close" if trunc_before is not None else kind)), ("接續", x, kind)):
        if tag == "接續" and trunc_before is None:
            continue
        if kk == "open":
            px = S.at[xx, "ao"]; tm = TRI[prev_day(xx)]; win = S[(S.index >= e) & (S.index < xx)]["ac"]
        else:
            xx = S[(S.index <= xx) & S["ok"]].index[-1]
            px = S.at[xx, "ac"]; tm = TRI[xx]; win = S[(S.index >= e) & (S.index <= xx)]["ac"]
        R = px / P0 - 1 - COST; M = tm / t0 - 1
        out[tag] = {"進場日": str(e.date()), "出場日": str(xx.date()), "R": R, "M": M, "X": R - M, "H": float(win.max() / P0 - 1)}
    return out


def close(a, b):
    return bool(np.isfinite(a) and np.isfinite(b) and (abs(a - b) < 1e-6 or abs(a - b) / max(abs(b), 1e-12) < 1e-6))


def main():
    TB = pd.read_csv(os.path.join(OUT, "table.csv"), dtype={"代號": str}, encoding="utf-8-sig", keep_default_na=False, na_values=[""])
    LP = pd.read_csv(os.path.join(OUT, "lamps_input.csv"), dtype=str, keep_default_na=False)
    MJ = json.load(open(os.path.join(OUT, "main.json"), encoding="utf-8"))
    res = {}
    # K1
    picks = [("貨櫃航運2020-21", "2603", "L2", "E1", None), ("矽晶圓2016-18", "6488", "L2", "抱250", None),
             ("MLCC2022-24", "2327", "L1", "E1", pd.Timestamp("2022-10-31")), ("重電2021-24", "1519", "L2", "抱625", None),
             ("光通訊2023-26", "3081", "L3", "E1", None)]
    k1 = []
    for seg, sid, L, X, tb in picks:
        c = cell(seg, sid, L, X, LP, tb)
        t = TB[(TB["段"] == seg) & (TB["代號"] == sid) & (TB["進場燈"] == L) & (TB["出場欄"] == X)].iloc[0]
        m = c["main"]
        ok = (m["進場日"] == t["進場日"] and m["出場日"] == t["出場日"] and close(m["R"], t["報酬R(扣0.4425%)"]) and close(m["M"], t["大盤報酬"])
              and close(m["X"], t["超額"]) and close(m["H"], t["天花板_格內"]))
        d = {"格": f"{seg} {sid} {L}→{X}", "重算": m, "表": {"進場日": t["進場日"], "出場日": t["出場日"], "R": t["報酬R(扣0.4425%)"], "M": t["大盤報酬"],
                                                           "X": t["超額"], "H": t["天花板_格內"]}, "相同": ok}
        if "接續" in c:
            b = c["接續"]
            okb = (b["出場日"] == t["接續出場日"] and close(b["R"], t["接續R(參考)"]) and close(b["M"], t["接續大盤"]) and close(b["X"], t["接續超額(參考)"])
                   and close(b["H"], t["接續天花板_格內"]))
            d["接續重算"] = b; d["接續相同"] = okb; ok = ok and okb
        k1.append(d)
        say(f"[K1] {d['格']}：{'相同' if ok else '⛔ 不同'}｜重算 R {m['R']:+.6f} 表 {t['報酬R(扣0.4425%)']:+.6f}｜超額 {m['X']:+.6f} 表 {t['超額']:+.6f}"
            + (f"｜接續 R {c['接續']['R']:+.6f} 表 {t['接續R(參考)']:+.6f}" if "接續" in c else ""))
        d["相同"] = ok
    # 6488 L2 到資料尾天花板（資料尾 ＝ main.json 資料尾）
    S, _ = stock("6488"); e = first_open(S, "2016-12"); tail = pd.Timestamp(MJ["資料尾"])
    h = float(S[(S.index >= e) & (S.index <= tail)]["ac"].max() / S.at[e, "ao"] - 1)
    t = TB[(TB["代號"] == "6488") & (TB["進場燈"] == "L2")].iloc[0]["天花板_到資料尾"]
    k1.append({"格": "6488 L2 天花板到資料尾", "重算": h, "表": t, "相同": close(h, t)}); say(f"[K1] 6488 L2 到資料尾天花板 重算 {h:+.6f} 表 {t:+.6f}")
    res["K1"] = k1
    # K2
    last_m = pd.Period(MJ["資料尾"][:7], "M")
    tail = pd.Timestamp(MJ["資料尾"])
    exp = []
    for _, r in LP.iterrows():
        for L in ("L1", "L2", "L3"):
            for X in ("E1", "E2", "E3", "抱250", "抱625"):
                if r[L] == "NA":
                    why = "進場燈NA"
                elif X.startswith("E") and r[X] == "NA":
                    why = "出場燈NA"
                elif X.startswith("E") and pd.Period(r[X], "M") + 1 > last_m:
                    why = "未到"
                elif X.startswith("E") and pd.Period(r[X], "M") <= pd.Period(r[L], "M"):
                    why = "出場不晚於進場"
                elif not X.startswith("E"):
                    S_, _ = stock(r["代號"]); e = first_open(S_, r[L]); k = DAYS.searchsorted(e) + int(X[1:]) - 1
                    why = "未到" if (k >= len(DAYS) or DAYS[k] > tail) else ""
                else:
                    why = ""
                exp.append((r["段"], r["代號"], L, X, why))
    E_ = pd.DataFrame(exp, columns=["段", "代號", "進場燈", "出場欄", "留空原因"])
    got = TB[["段", "代號", "進場燈", "出場欄", "留空原因"]].fillna("")
    k2 = bool(len(E_) == len(got) and (E_.reset_index(drop=True) == got.reset_index(drop=True)).all().all())
    res["K2"] = {"格數": len(E_), "逐格相同": k2, "留空計數": E_[E_["留空原因"] != ""]["留空原因"].value_counts().to_dict()}
    say(f"[K2] 留空原因 465 格逐格相同：{k2}｜{res['K2']['留空計數']}")
    # K3
    md = open(os.path.join(OUT, "summary.md"), encoding="utf-8").read()
    hf = {}
    for sid in ("1503", "1513"):
        S, _ = stock(sid); w = S[(S.index >= "2021-05-01") & (S.index <= "2024-12-31") & S["ok"]]["ac"]
        hf[sid] = str(w.idxmax().to_period("M"))
    k3 = {"警語在表頭": md.split("\n")[2].find(WARN) >= 0, "警語次數": md.count(WARN), "高點月重算": hf,
          "高點月相同": all(hf[s] == MJ["高點月補"][s]["高點月"] for s in hf)}
    res["K3"] = k3; say(f"[K3] {k3}")
    allok = all(d["相同"] for d in k1) and k2 and k3["警語在表頭"] and k3["高點月相同"]
    res["全部相同"] = allok; say(f"[結論] 全部相同：{allok}")
    json.dump(res, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    open(os.path.join(OUT, "check.log"), "w", encoding="utf-8").write("\n".join(LOGS) + "\n")


if __name__ == "__main__":
    main()

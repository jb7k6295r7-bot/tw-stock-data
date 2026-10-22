# -*- coding: utf-8 -*-
"""長線三問 丙（F1～F7 賣法）加描述欄「賣出的錢改抱大盤報酬指數到評估點」——回測線計算子代理（描述、不計 N）。
依據：裁定 seq458 §四.2（准，只當描述；判定與主結論仍照使用者口徑「賣掉的錢不計」，另一口徑寫一句說明，⛔ 不並列兩組結論）、
     台股策略線 0013 §四.2（F1～F3 與 §四b F4～F7，含使用者「利多反應完＋股價高漲就走」F7）。
⛔ 不改 researchLong3.py 與 resultsLong3/ 既有檔；只新增本檔、researchLong3_alt_check.py、resultsLong3/alt/。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchLong3_alt --dry --procs 3   # 乾跑（R 全 0）⇒ alt/dry/
    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchLong3_alt --procs 3         # 正式 ⇒ alt/
    對帳：PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchLong3_alt_check [--dry]

═══ 讀法（A 標；在讀任何新欄報酬之前寫死；★＝執行者定）═══
 A1 重建（⛔ 不寫第二份）：researchLong3 的丙賣法寫在 main() 內（沒有可單獨 import 的函式）⇒ 本檔直接呼叫 researchLong3.main()（OUT 轉到 /tmp/l3a_rebuild_*，
    ⛔ 不碰 resultsLong3/），在它寫 long3.json 那一刻取 main() 的區域變數（SS、CR、TC、CAL…）。
    對帳：重建的 丙_表.csv、events_丙.csv.gz（解壓後）須與已提交檔【逐位元組】相同，否則中止、⛔ 不算新欄。
 A2 大盤報酬指數 ＝ origin/main data/history/market_tri.csv（只有收盤）。某日無指數值 ⇒ 用該日或之前最後一個值 ★（筆數照報）。
 A3 新欄（每法 F、每筆被賣出者）：賣得的錢於【賣出日收盤】買進大盤報酬指數 ★（賣在開盤、指數只有收盤 ⇒ 賣出當天開盤到收盤這段不計），
    持有到【抱 3 年的出場日】收盤（＝ 原 d 的評估點，含壞根前一根、下市末根）；★ 扣 ETF 來回 0.385%（手續費 0.285%＋ETF 證交稅 0.1%，同 researchLong3 L13 COST50）。
      賣法＋改抱大盤 ＝ (1＋賣價÷進場開盤−1) × (TRI[抱3年出場日] ÷ TRI[賣出日] − 0.385%) − 1
      d_alt ＝ 賣法＋改抱大盤 − 抱 3 年；沒被賣的 ⇒ d_alt ＝ 0（同原 d）。
 A4 對抱 1 年（同原表兩讀法）：
      d1_alt ＝ 同一賣法（3 年窗、錢改抱大盤到抱 3 年出場日）− 抱 250 日；沒被賣 ⇒ ＝ 原 d1（抱 3 年 − 抱 1 年）。
      d1′_alt ＝ 賣法只在 1 年窗內作用：賣出那根 ≤ 抱 1 年出場根 ⇒ 錢改抱大盤到【抱 1 年出場日】收盤（同扣 0.385%）− 抱 1 年；否則 0（同原 d1′）。
      抱 1 年出場根由 researchLong3.exits_vec（e＋249）重算，抱 3 年出場根同法重算並須與 events_丙 的 抱3年出場日 相同。
 A5 統計同原表：進場段（全部窗完整／早年進場(～2014)／2015～進場／探索進場(2017-03～2021-12)）、窗完整 ∧ 抱3年R 有值；
    進場月分群 1.96（researchLong3.stats）；描述（不計 N）。
 A6 呈現（seq458 §四.2）：原口徑「記 0」欄與原結果句一字不改照留；新欄只寫成一句「若賣掉的錢改買大盤：…」附在後面，⛔ 不做成兩組並列結論、⛔ 不改判語。
    措辭照 seq343：真頂訊號（多半在最高點之前）；F7 附句照原。
 A7 乾跑（--dry）：新欄的輸入全部換成 0（賣價報酬、抱 3 年、抱 1 年 R ＝ 0，指數 ＝ 常數 1）⇒ 所有欄位跑通，輸出 alt/dry/；重建與對帳照常。
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json as _json
import os
import subprocess
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import researchLong3 as L3                    # noqa: E402  main（丙事件與賣法）、exits_vec、stats、COST50、FS、FNAME、pct、fmtp

ORIG = "backtest/resultsLong3"
OUT0 = "backtest/resultsLong3/alt"
TRI_PATH = "data/history/market_tri.csv"
C_ETF = L3.COST50
LOG: list = []
_CAP: dict = {}


def log(s):
    s = f"[{pd.Timestamp.now(tz='Asia/Taipei').strftime('%H:%M:%S')}] {s}"
    print(s, flush=True); LOG.append(s)


class _JsonShim:
    """researchLong3.main() 寫 long3.json 時取它的區域變數（⛔ 不改 researchLong3 任何一行）。"""
    def dump(self, obj, fp, *a, **k):
        _CAP.update(sys._getframe(1).f_locals)
        return _json.dump(obj, fp, *a, **k)

    def __getattr__(self, n):
        return getattr(_json, n)


def rebuild(procs, tag):
    reb = f"/tmp/l3a_rebuild_{tag}"
    os.makedirs(reb, exist_ok=True)
    L3.OUT = reb
    L3.json = _JsonShim()
    argv0 = sys.argv
    sys.argv = ["researchLong3", "--procs", str(procs)]
    try:
        L3.main()
    finally:
        sys.argv = argv0
    if "CR" not in _CAP:
        raise SystemExit("⛔ 沒取到 researchLong3.main() 的區域變數")
    return reb


def gz_text(p):
    return gzip.open(p, "rb").read()


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--procs", type=int, default=3); ap.add_argument("--dry", action="store_true")
    a = ap.parse_args()
    t0 = time.time()
    OUT = os.path.join(OUT0, "dry") if a.dry else OUT0
    os.makedirs(OUT, exist_ok=True)
    log(f"[開始] {'乾跑（R 全 0）' if a.dry else '正式'}｜輸出 {OUT}")
    # ── A1 重建
    reb = rebuild(a.procs, "dry" if a.dry else "real")
    log(f"[重建完] researchLong3.main() ⇒ {reb}｜{time.time() - t0:.0f}s")
    same_tc = open(os.path.join(reb, "丙_表.csv"), "rb").read() == open(os.path.join(ORIG, "丙_表.csv"), "rb").read()
    same_ev = gz_text(os.path.join(reb, "events_丙.csv.gz")) == gz_text(os.path.join(ORIG, "events_丙.csv.gz"))
    TCo = pd.read_csv(os.path.join(ORIG, "丙_表.csv"))
    log(f"[對帳] 丙_表.csv 逐位元組相同 {same_tc}（{len(TCo)} 列）｜events_丙 解壓後逐位元組相同 {same_ev}")
    if not (same_tc and same_ev):
        raise SystemExit("⛔ 重建 ≠ 已提交丙 ⇒ 中止（未算新欄）")
    L = _CAP
    SS, CR, CAL, CEND, ne, TC, SC = L["SS"], L["CR"].copy(), L["CAL"], L["CEND"], L["ne"], L["TC"], L["SC"]
    CSEG = L["CSEG"]; CP = L["CP"]
    # ── A2 指數
    head = subprocess.run(["git", "rev-parse", "origin/main"], capture_output=True, text=True).stdout.strip()
    blob = subprocess.run(["git", "show", f"origin/main:{TRI_PATH}"], capture_output=True, check=True).stdout
    T = pd.read_csv(io.BytesIO(blob), parse_dates=["date"]).sort_values("date")
    if not (np.isfinite(T["close"]).all() and (T["close"] > 0).all()):
        raise SystemExit("⛔ 指數有缺值或 ≤0")
    td = T["date"].to_numpy(); tv = T["close"].to_numpy(float)
    k = np.searchsorted(td, CAL.to_numpy(), side="right") - 1
    if (k < 0).any():
        raise SystemExit("⛔ 指數起點晚於日曆起點")
    TRIc = tv[k]
    exact = td[k] == CAL.to_numpy()
    J = {"性質": "長線三問 丙 加描述欄『賣出的錢改抱大盤報酬指數到評估點』（描述、不計 N）", "乾跑": bool(a.dry),
         "依據": "裁定 seq458 §四.2；台股策略線 0013 §四.2", "讀法": __doc__.split("═══ 讀法")[1],
         "重建": {"來源": "researchLong3.main()（OUT 轉 /tmp、⛔ 不碰 resultsLong3）", "丙_表逐位元組相同": same_tc, "events_丙逐位元組相同": same_ev, "丙_表列數": int(len(TCo))},
         "指數": {"檔": f"origin/main:{TRI_PATH}", "origin_main": head, "sha256": hashlib.sha256(blob).hexdigest()[:16], "列": int(len(T)),
                 "起": str(T["date"].iloc[0].date()), "迄": str(T["date"].iloc[-1].date()), "日曆日無指數值(用之前最後值)": int((~exact).sum())},
         "ETF來回成本": C_ETF}
    log(f"[指數] {J['指數']}")
    if a.dry:
        TRIc = np.ones_like(TRIc)
    # ── A3／A4 逐筆
    ROW = []
    nchk_x3 = 0; n_tri_inexact = {"賣出日": 0, "評估點": 0}
    for _, rw in CR.iterrows():
        s = rw["sid"]; e = int(rw["e"]); S = SS[s]; pos = S["pos"]
        ke, kx, ty = L3.exits_vec(S, np.array([e, e]), np.array([e + 749, e + 249]), CEND, ne)
        kx3, kx1 = int(kx[0]), int(kx[1])
        x3 = int(pos[kx3]) if kx3 >= 0 else -1; x1 = int(pos[kx1]) if kx1 >= 0 else -1
        if (str(CAL[x3].date()) if kx3 >= 0 else "") != (rw["抱3年出場日"] if isinstance(rw["抱3年出場日"], str) else ""):
            raise SystemExit(f"⛔ {s} {e} 抱3年出場日 重算 ≠ events_丙")
        nchk_x3 += 1
        b3 = 0.0 if a.dry else rw["抱3年R"]; b1 = 0.0 if a.dry else rw["抱1年R"]
        b3 = b3 if np.isfinite(rw["抱3年R"]) else np.nan; b1 = b1 if np.isfinite(rw["抱1年R"]) else np.nan
        rec = {"sid": s, "期別": rw["期別"], "e": e, "進場日": rw["進場日"], "進場月": rw["進場月"], "窗完整": bool(rw["窗完整"]), "typ3": int(rw["typ3"]),
               "typ1": int(rw["typ1"]), "抱3年R": b3, "抱1年R": b1, "抱3年出場日": str(CAL[x3].date()) if x3 >= 0 else "",
               "抱1年出場日": str(CAL[x1].date()) if x1 >= 0 else ""}
        if x3 >= 0 and not exact[x3]:
            n_tri_inexact["評估點"] += 1
        for F in L3.FS:
            sold = bool(rw[f"{F}_賣"])
            rec[f"{F}_賣"] = sold
            rec[f"{F}_d"] = 0.0 if (a.dry and np.isfinite(rw[f"{F}_d"])) else rw[f"{F}_d"]
            rec[f"{F}_d1"] = (b3 - b1 if not sold else 0.0 - b1) if a.dry else rw[f"{F}_d1"]
            rec[f"{F}_d1alt"] = 0.0 if (a.dry and np.isfinite(rw[f"{F}_d1alt"])) else rw[f"{F}_d1alt"]
            if sold:
                ps = CP[rw[f"{F}_賣日"]]
                if not exact[ps]:
                    n_tri_inexact["賣出日"] += 1
                sv = 0.0 if a.dry else rw[f"{F}_R"]
                g3 = TRIc[x3] / TRIc[ps]
                alt3 = (1.0 + sv) * (g3 - C_ETF) - 1.0
                rec[f"{F}_賣日"] = rw[f"{F}_賣日"]; rec[f"{F}_賣R"] = sv
                rec[f"{F}_改抱大盤R"] = g3 - 1.0
                rec[f"{F}_賣法加大盤R"] = alt3
                rec[f"{F}_d_alt"] = alt3 - b3
                rec[f"{F}_d1_alt"] = alt3 - b1 if np.isfinite(b1) else np.nan
                if np.isfinite(b1):
                    if ps <= x1:
                        alt1 = (1.0 + sv) * (TRIc[x1] / TRIc[ps] - C_ETF) - 1.0
                        rec[f"{F}_d1alt_alt"] = alt1 - b1
                    else:
                        rec[f"{F}_d1alt_alt"] = 0.0
                else:
                    rec[f"{F}_d1alt_alt"] = np.nan
            else:
                rec[f"{F}_d_alt"] = 0.0 if np.isfinite(b3) else np.nan
                rec[f"{F}_d1_alt"] = (b3 - b1) if (np.isfinite(b1) and np.isfinite(b3)) else np.nan
                rec[f"{F}_d1alt_alt"] = 0.0 if np.isfinite(b1) else np.nan
        ROW.append(rec)
    EV = pd.DataFrame(ROW)
    J["逐筆"] = {"筆數": int(len(EV)), "抱3年出場日重算相符": nchk_x3, "指數非當日值": n_tri_inexact}
    log(f"[逐筆] {J['逐筆']}｜{time.time() - t0:.0f}s")
    # 原 d 在新逐筆檔與原逐筆檔相同（正式跑）
    if not a.dry:
        for F in L3.FS:
            for c in ("d", "d1", "d1alt"):
                x = EV[f"{F}_{c}"].to_numpy(float); y = CR[f"{F}_{c}"].to_numpy(float)
                if not np.array_equal(x, y, equal_nan=True):
                    raise SystemExit(f"⛔ {F}_{c} 搬運不同")
    # ── A5 表
    TB = []
    for sg, (a0, a1) in CSEG.items():
        sub = EV[(EV["e"] >= a0) & (EV["e"] <= a1) & EV["窗完整"] & np.isfinite(EV["抱3年R"])]
        o = TCo[(TCo["進場段"] == sg)].set_index("法")
        for F in L3.FS:
            sold = sub[sub[f"{F}_賣"]]
            km = sub["進場月"].to_numpy()
            st0 = L3.stats(sub[f"{F}_d"].to_numpy(), km)
            sta = L3.stats(sub[f"{F}_d_alt"].to_numpy(), km)
            st1 = L3.stats(sub[f"{F}_d1"].to_numpy(), km); st1a = L3.stats(sub[f"{F}_d1_alt"].to_numpy(), km)
            st2 = L3.stats(sub[f"{F}_d1alt"].to_numpy(), km); st2a = L3.stats(sub[f"{F}_d1alt_alt"].to_numpy(), km)
            stv = L3.stats(sold[f"{F}_d_alt"].to_numpy(), sold["進場月"].to_numpy()) if len(sold) else {}
            TB.append({"進場段": sg, "法": F, "說明": L3.FNAME[F], "事件(窗完整)": int(len(sub)), "觸發賣出": int(len(sold)),
                       "d平均(原：賣掉的錢記0)": st0.get("平均"), "d_lo": st0.get("lo196"), "d_hi": st0.get("hi196"), "d結果(描述)": st0.get("結果196"),
                       "d_alt平均(賣掉的錢改抱大盤)": sta.get("平均"), "d_alt中位": sta.get("中位"), "d_alt_lo": sta.get("lo196"), "d_alt_hi": sta.get("hi196"),
                       "d_alt結果(描述)": sta.get("結果196"), "d_alt_n_eff": sta.get("n_eff"),
                       "差(d_alt−d)": (sta.get("平均") - st0.get("平均")) if (sta.get("平均") is not None and st0.get("平均") is not None) else None,
                       "被賣者d_alt平均": stv.get("平均"), "被賣者d_alt中位": stv.get("中位"),
                       "被賣者改抱大盤R平均(未扣)": float(sold[f"{F}_改抱大盤R"].mean()) if len(sold) else None,
                       "被賣者改抱大盤R中位(未扣)": float(sold[f"{F}_改抱大盤R"].median()) if len(sold) else None,
                       "d1平均(原，對抱1年)": st1.get("平均"), "d1_alt平均": st1a.get("平均"), "d1_alt_lo": st1a.get("lo196"), "d1_alt_hi": st1a.get("hi196"),
                       "d1′平均(原，1年窗)": st2.get("平均"), "d1′_alt平均": st2a.get("平均"), "d1′_alt_lo": st2a.get("lo196"), "d1′_alt_hi": st2a.get("hi196"),
                       "原表d平均": o.at[F, "d平均(加賣法−抱3年)"], "原表d1平均": o.at[F, "d1平均(對抱1年)"], "原表d1′平均": o.at[F, "d1′平均(1年窗另一讀法)"],
                       "性質": "描述（不計 N）；新欄只當描述，⛔ 不並列判定"})
    TB = pd.DataFrame(TB)
    if not a.dry:
        for c0, c1 in (("d平均(原：賣掉的錢記0)", "原表d平均"), ("d1平均(原，對抱1年)", "原表d1平均"), ("d1′平均(原，1年窗)", "原表d1′平均")):
            mx = float(np.nanmax(np.abs(TB[c0].to_numpy(float) - TB[c1].to_numpy(float))))
            if mx > 1e-12:
                raise SystemExit(f"⛔ 原欄 {c0} 與原表差 {mx:.2e}")
        J["原欄與原表"] = "相符（≤1e−12）"
    # ── A6 句
    SENT = {}
    for F in L3.FS:
        r = TB[(TB["進場段"] == "全部窗完整") & (TB["法"] == F)].iloc[0]
        w = {"結果②": "多", "結果③": "少"}.get(r["d_alt結果(描述)"], "分不出，差")
        m_ = r["d_alt平均(賣掉的錢改抱大盤)"]
        mtxt = L3.fmtp(abs(m_), 2) if w in ("多", "少") else L3.pct(m_)
        SENT[F] = (SC[F] + f"｜若賣掉的錢改買大盤（報酬指數，賣出日收盤買、抱 3 年那天收盤賣，扣 0.385%）：比抱 3 年{w} {mtxt}"
                   f"（CI {L3.pct(r['d_alt_lo'])}～{L3.pct(r['d_alt_hi'])}），對抱 1 年 {L3.pct(r['d1_alt平均'])}（只是描述，判語照上）")
        log(f"[句] {F}：{SENT[F]}")
    J["丙句(原句一字不改＋若改買大盤一句)"] = SENT
    J["表"] = TB.to_dict("records")
    J["時間"] = pd.Timestamp.now(tz="Asia/Taipei").strftime("%Y-%m-%d %H:%M")
    TB.to_csv(os.path.join(OUT, "丙_alt_表.csv"), index=False, encoding="utf-8-sig")
    EV.to_csv(os.path.join(OUT, "events_丙_alt.csv.gz"), index=False, compression="gzip")
    _json.dump(J, open(os.path.join(OUT, "long3_alt.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    log(f"[完] {time.time() - t0:.0f}s")
    open(os.path.join(OUT, "run.log"), "w", encoding="utf-8").write("\n".join(LOG) + "\n")


if __name__ == "__main__":
    main()

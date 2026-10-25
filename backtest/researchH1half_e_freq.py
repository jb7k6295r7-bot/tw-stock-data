# -*- coding: utf-8 -*-
"""H1「營收見頂確認、先賣一半」seq1：電子＋傳產普查（清單 v4）頻率表（同一登錄 sha 42d64aee7df4e61b；讀法照裁定 seq475：滑動窗、E 照字面）——回測線計算子代理。
⛔ 本檔不算任何報酬；⛔ 不 commit、不改既有檔（傳產原結果 resultsH1half/freq、main 不覆寫）。
事件與進場 ＝ 普查 commit 8c4d0d9559 的輸出（backtest/resultsLampCensus/rows.csv、signals.csv、caps.csv，git show 讀該版，不讀工作樹）；
  主程式用同版 researchLampCensus.Engine.entry 逐筆重算進場日，⛔ 不同即停。觸發邏輯（F1～F8、F5′）import researchH1half_freq（同一套，已過 freq_check）。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchH1half_e_freq
    對帳：PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchH1half_e_freq_check
輸出 backtest/resultsH1half/freq_e/：events.csv、freq.csv、freq.md、main.json、run.log

═══ 讀法（★＝執行者定；其餘照 researchH1half_freq F0～F10）═══
 E0 清單：傳產 v4（附件-近年燈號普查訊號清單v4_加判定把握_產業分析線-20261025-1830.csv）＋電子 v4（附件-電子類燈號普查訊號清單v4_產業分析線-20261025-2150.csv）；
    訊號鍵、類（電子／傳產）、甲乙、無點名、規模下限、兩可、燈2兩可、自評知道 一律取普查 8c4d0d9559 輸出（同版 load_signals 讀法）。
 E1 情境（照普查 L8）：照實＝全部；寬鬆＝兩可都算亮燈（清單本來就列入 ⇒ ＝照實，主程式驗證兩者事件集合相同）；
    嚴格＝燈 1「判定把握」＝兩可的訊號列不算（燈 2 兩可只影響加碼，H1 無加碼 ⇒ 不影響）；剔自評知道＝照實減掉「判燈者自評知道後來走勢」＝知道的訊號。
 E2 類別：電子、傳產分開，再報合計；甲乙分開；型照清單（缺貨／新需求／政策；清單另有型照列）。季分群 n_eff ＝ 燈 1 季不同季數（各格自己算）。
 E3 自評知道比例 ＝ 自評欄＝知道的訊號列 ÷ 該類全部訊號列（另報 ÷ 進統計訊號）。
"""
from __future__ import annotations

import io
import json
import os
import subprocess
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import researchH1half_freq as F               # noqa: E402

CREV = "8c4d0d9559"
LC8 = F._frozen("researchLampCensus_at_8c4d0d9559", "backtest/researchLampCensus.py", CREV)
OUT = "backtest/resultsH1half/freq_e"
SRCS = ["/mnt/c/SynologyDrive/跨線信箱/附件-近年燈號普查訊號清單v4_加判定把握_產業分析線-20261025-1830.csv",
        "/mnt/c/SynologyDrive/跨線信箱/附件-電子類燈號普查訊號清單v4_產業分析線-20261025-2150.csv"]
CLASSES = ("電子", "傳產", "合計")
SCEN = ("照實", "寬鬆", "嚴格", "剔自評知道")
LOG = []


def log(s):
    s = f"[{time.strftime('%H:%M:%S')}] {s}"; print(s, flush=True); LOG.append(s)


def cshow(p, **kw):
    t = subprocess.run(["git", "show", f"{CREV}:{p}"], capture_output=True, check=True).stdout
    return pd.read_csv(io.BytesIO(t), **kw)


def census_out():
    RW = cshow("backtest/resultsLampCensus/rows.csv", dtype={"代號": str})
    SG = cshow("backtest/resultsLampCensus/signals.csv", dtype={"訊號": str})
    CP = cshow("backtest/resultsLampCensus/caps.csv", dtype={"代號": str})
    for f, k in zip(SRCS, ("signals_input.csv", "signals_input_2.csv")):
        a = open(f, "rb").read(); b = subprocess.run(["git", "show", f"{CREV}:backtest/resultsLampCensus/{k}"], capture_output=True, check=True).stdout
        if a != b:
            raise SystemExit(f"⛔ 清單 {os.path.basename(f)} 與普查 {CREV} 的 {k} 不同")
    return RW, SG, CP


def tf(x):
    return x.astype(str).str.strip().str.lower().eq("true")


def build_events(EN, C, L):
    RW, SG, CP = census_out()
    S, info = LC8.load_signals(SRCS)
    sk = SG.set_index("訊號")
    for c in ("甲", "乙", "無點名", "兩可", "燈2兩可", "自評知道"):
        a = S.set_index("訊號")[c].astype(bool); b = tf(sk[c]).reindex(a.index)
        if not a.equals(b):
            raise SystemExit(f"⛔ load_signals 重讀與普查 signals.csv 的「{c}」不同")
    R1 = RW[(RW["段"] == "燈1") & (RW["H"].astype(str) == "末")].copy()
    R1 = pd.concat([R1, RW[(RW["段"] == "燈1") & RW["進場日"].isna() & ~RW.index.isin(R1.index)]]).drop_duplicates(["訊號", "代號"])
    rows = []; Sc = {}; nchk = 0
    for _, s in S.iterrows():
        base = {"樣本": "普查", "訊號": s["訊號"], "類": s["類"], "版本": s["版本"], "甲": bool(s["甲"]), "乙": bool(s["乙"]), "型": s["型"], "產業": s["產業"],
                "主題": s["主題"], "燈1季": s["燈1季"], "無點名": bool(s["無點名"]), "兩可": bool(s["兩可"]), "自評知道": bool(s["自評知道"])}
        if s["無點名"]:
            rows.append({**base, "代號": "", "入選": False, "下限": "無點名"}); continue
        sub = R1[R1["訊號"] == s["訊號"]]
        cp = CP[CP["訊號"] == s["訊號"]]
        for _, c in cp.iterrows():
            sid = c["代號"] if isinstance(c["代號"], str) else ""
            flag = c["判定"]
            rec = {**base, "代號": sid, "名稱": c["名稱"], "下限": flag, "入選": flag in ("過下限", "查無、未剔除"), "市值(億)": c.get("市值(億)")}
            if not sid:
                rows.append({**rec, "入選": False, "結果": "代號讀不出"}); continue
            r = sub[sub["代號"] == sid]
            ent = EN.entry(sid, LC8.q_last_month(s["燈1季"]))
            if ent[0] is None:
                if len(r) and isinstance(r["進場日"].iloc[0], str):
                    raise SystemExit(f"⛔ {s['訊號']} {sid} 進場重算失敗但普查有進場日")
                rows.append({**rec, "入選": False, "結果": ent[1]}); continue
            i, e, dl = ent
            if not len(r) or str(r["進場日"].iloc[0]) != str(EN.CAL[e].date()) or bool(tf(r["入選"]).iloc[0]) != rec["入選"]:
                raise SystemExit(f"⛔ {s['訊號']} {sid} 進場日／入選與普查 {CREV} 不同（{r['進場日'].tolist()} vs {EN.CAL[e].date()}）")
            nchk += 1
            rec.update({"進場日": str(EN.CAL[e].date()), "進場順延日": int(dl), "_i": i, "_e": e})
            if sid not in Sc:
                Sc[sid] = F.s_series(L, sid)
            Sx, rng = Sc[sid]
            rec["營收期別"] = "" if rng is None else f"{rng[0]}～{rng[1]}"
            rows.append({**rec, **F.h1_trigger(Sx, C, i, e)})
    EV = pd.DataFrame(rows)
    n_r1 = int(R1["進場日"].notna().sum())
    if nchk != n_r1:
        raise SystemExit(f"⛔ 進場驗證筆數 {nchk} ≠ 普查有進場日的列 {n_r1}")
    return EV, S, info, {"進場日逐筆相同": nchk, "普查版": CREV}


def scen_mask(df, sc):
    if sc in ("照實", "寬鬆"):
        return pd.Series(True, index=df.index)
    if sc == "嚴格":
        return ~df["兩可"].astype(bool)
    return ~df["自評知道"].astype(bool)


def main():
    t0 = time.time(); os.makedirs(OUT, exist_ok=True)
    s16 = F.reg_sha16()
    if s16 != F.REG_SHA16:
        raise SystemExit(f"⛔ 登錄 sha {s16} ≠ {F.REG_SHA16}")
    EN = LC8.Engine(); C = F.Cal(EN)
    L, diag, MD = F.load_S()
    EV, S, info, chk = build_events(EN, C, L)
    log(f"[進場驗證] {chk}｜清單資訊 有判定把握 {info['有判定把握欄']}、有自評 {info['有自評欄']}")
    keep = ["樣本", "訊號", "類", "版本", "甲", "乙", "型", "產業", "主題", "燈1季", "無點名", "兩可", "自評知道", "代號", "名稱", "下限", "市值(億)", "入選",
            "進場日", "進場順延日", "E日", "未到", "截斷", "截斷日", "營收期別", "m0", "可用月數", "S空月數", "P終", "P終月", "結果", "P", "P月", "確認月",
            "S1", "S2", "S3", "第3月≤0", "第3月≤P/2", "J日", "確認距m0月", "賣出日", "賣出順延日", "時距月", "15日規則改日", "緊接版觸發", "註"]
    EV.reindex(columns=keep).to_csv(os.path.join(OUT, "events.csv"), index=False, encoding="utf-8-sig")
    types = [t for t in ("缺貨", "新需求", "政策") if t in set(S["型"])] + sorted(set(S["型"]) - {"缺貨", "新需求", "政策"})
    inn_all = EV[EV["入選"].astype(bool) & EV["代號"].ne("") & EV["結果"].notna()]
    if "營收全缺" in set(inn_all["結果"]):
        log("⚠ 有營收全缺件")
    FQ = []
    for sc in SCEN:
        for cl in CLASSES:
            for ver in ("甲", "乙"):
                sig = S[S[ver] & (S["類"] == cl if cl != "合計" else True)]
                sig = sig[scen_mask(sig, sc)]
                inn = inn_all[inn_all[ver] & (inn_all["類"] == cl if cl != "合計" else True)]
                inn = inn[scen_mask(inn, sc)]
                for ty in ("全部",) + tuple(types):
                    sg_ = sig if ty == "全部" else sig[sig["型"] == ty]
                    sub = inn if ty == "全部" else inn[inn["型"] == ty]
                    if ty != "全部" and not len(sg_):
                        continue
                    m, ov, ml = F.overlap(sub) if len(sub) else (0, 0, "")
                    FQ.append({"情境": sc, "類": cl, "組": ver, "型": ty, "訊號列": len(sg_), "無點名": int(sg_["無點名"].sum()), "兩可列": int(sg_["兩可"].sum()),
                               "自評知道列": int(sg_["自評知道"].sum()), **F.block(sub), "重疊代號(≥2訊號)": m, "其中持有窗重疊": ov})
    FQ = pd.DataFrame(FQ)
    a = FQ[FQ["情境"] == "照實"].drop(columns="情境").reset_index(drop=True); b = FQ[FQ["情境"] == "寬鬆"].drop(columns="情境").reset_index(drop=True)
    if not a.fillna(-9).equals(b.fillna(-9)):
        raise SystemExit("⛔ 寬鬆 ≠ 照實（讀法 E1 需重訂）")
    FQ.to_csv(os.path.join(OUT, "freq.csv"), index=False, encoding="utf-8-sig")
    self_share = {}
    for cl in ("電子", "傳產"):
        sl = S[S["類"] == cl]; inn_sig = inn_all[inn_all["類"] == cl]["訊號"].unique()
        si = sl[sl["訊號"].isin(inn_sig)]
        self_share[cl] = {"訊號列": len(sl), "自評知道": int(sl["自評知道"].sum()), "比例(全部列)": float(sl["自評知道"].mean()) if len(sl) else np.nan,
                          "進統計訊號": len(si), "其中自評知道": int(si["自評知道"].sum()), "比例(進統計)": float(si["自評知道"].mean()) if len(si) else np.nan}
    meta = {"登錄sha16": s16, "普查版": CREV, "面板sha": EN.sha, "面板尾": str(EN.CAL[EN.CEND].date()), "revpit": MD, "進場驗證": chk, "清單": SRCS,
            "自評知道比例": self_share, "型": types}
    write_md(FQ, EV, meta)
    json.dump({**meta, "freq": FQ.to_dict("records"), "讀法": __doc__.split("═══ 讀法")[1], "秒": round(time.time() - t0)},
              open(os.path.join(OUT, "main.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1,
              default=lambda o: (None if not np.isfinite(o) else float(o)) if isinstance(o, (np.floating, np.integer, float)) else str(o))
    log(f"[自評知道] {self_share}")
    log(f"[完成] {OUT}｜{time.time() - t0:.0f}s")
    open(os.path.join(OUT, "run.log"), "w", encoding="utf-8").write("\n".join(LOG) + "\n")


def pc(v):
    return "—" if v is None or not np.isfinite(v) else f"{v * 100:.0f}%"


def f1(v, pct=False):
    if v is None or not np.isfinite(v):
        return "—"
    return f"{v * 100:+.0f}%" if pct else f"{v:.1f}"


def write_md(FQ, EV, meta):
    md = ["# H1 先賣一半 seq1：電子＋傳產普查（v4）頻率表（⛔ 不含任何報酬）", "",
          f"- 登錄 sha {meta['登錄sha16']}；讀法照裁定 seq475（滑動窗、E 照字面）；事件與進場＝普查 {meta['普查版']} 輸出（{meta['進場驗證']}）。",
          f"- 自評知道比例：{meta['自評知道比例']}", "- 寬鬆＝照實（主程式已驗事件集合相同），表中只列照實、嚴格、剔自評知道。", "",
          "| 情境 | 類 | 組 | 型 | 訊號列 | 無點名 | 兩可 | 自評知道 | 可交檔次 | 燈1季 n_eff | 觸發（緊接版） | 觸發比例 | 時距月中位 | P 中位 | 第3月 ≤0／≤P÷2且>0 | 未到 E | 營收有缺 | 未觸發：P≤0／到E未確認／未到末日前未確認／已先結算／營收全缺 |",
          "|" + "---|" * 18]
    for _, r in FQ[FQ["情境"] != "寬鬆"].iterrows():
        md.append(f"| {r['情境']} | {r['類']} | {r['組']} | {r['型']} | {int(r['訊號列'])} | {int(r['無點名'])} | {int(r['兩可列'])} | {int(r['自評知道列'])} | {r['可交檔次']} | "
                  f"{r['n_eff(群數)']} | {r['觸發']}（{r['緊接版觸發數']}） | {pc(r['觸發比例'])} | {f1(r['時距月_中位'])} | {f1(r['P_中位'], True)} | "
                  f"{r['第3月≤0']}／{r['第3月≤P/2且>0']} | {r['未到E件數']} | {r['營收有缺件數']} | "
                  f"{r['P≤0未觸發']}／{r['到E未確認']}／{r['未到E、末日前未確認']}／{r['觸發但已先結算']}／{r['營收全缺']} |")
    ins = EV[EV["入選"].astype(bool) & EV["代號"].ne("") & EV["結果"].notna()]
    md += ["", "## 註記", "",
           "- 未觸發件：" + ("；".join(f"{r.類} {r.訊號} {r.代號}（{r.結果}）" for r in ins.itertuples() if r.結果 != "觸發") or "無"),
           "- 營收有缺：" + ("；".join(f"{r.訊號} {r.代號}（缺 {int(r.S空月數)}／{int(r.可用月數)} 月）" for r in ins.itertuples() if (r.S空月數 or 0) > 0) or "無"),
           "- 截斷（壞根／下市）：" + ("；".join(f"{r.訊號} {r.代號}（{r.截斷}）" for r in ins.itertuples() if isinstance(r.截斷, str) and r.截斷) or "無"),
           "- 規模下限剔除（不進統計）：" + ("；".join(f"{r.訊號} {r.代號}" for r in EV[EV['下限'] == '市值不足、剔除'].itertuples()) or "無"),
           "- 進場失敗／代號讀不出：" + ("；".join(f"{r.訊號} {r.代號}（{r.結果}）" for r in EV[~EV['入選'].astype(bool) & EV['結果'].notna() & (EV['下限'] != '市值不足、剔除')].itertuples()) or "無"),
           "- 5371 中光電三件營收全缺（PIN 版 revenue_hist：5371 只到 2012-12、3718 從 2026-08 起 ⇒ 2013-01～2026-07 本庫無此公司月營收，資料庫缺口）⇒ 照讀法記「營收全缺」、未觸發，⛔ 未自行接代號。",
           "- ⛔ 兩版（H1、全抱）都沒套 v4.1 新聞出場 ①～⑤。本表不含任何報酬。"]
    open(os.path.join(OUT, "freq.md"), "w", encoding="utf-8").write("\n".join(md) + "\n")


if __name__ == "__main__":
    main()

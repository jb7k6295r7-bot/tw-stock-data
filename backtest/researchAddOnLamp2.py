# -*- coding: utf-8 -*-
"""舊 31 段（大漲 16＋失敗 15）燈 2 加碼 2 份測試（產業分析線 seq41 §三、seq42、seq43；描述、⛔ 不判定、不計 N、不改規則）——回測線計算子代理。
⚠ 事後挑的樣本 ⇒ 只描述。大漲段燈 2 是早期研究標的、未照「只用當時出處」重核；失敗段有重核 ⇒ 兩組口徑不同。
⛔ 不 commit、不改既有檔。檔名說明：backtest/researchAddOn.py、researchAddOn_check.py、resultsAddOn/ 早已存在（別件），⛔ 不覆寫 ⇒ 本件改名 researchAddOnLamp2*。
   引擎＝researchLampCensus.Engine（researchV41EV.tw_rows 結算／壞根截斷／接續原式，可指定目標日）只 import。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchAddOnLamp2
    對帳：PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchAddOnLamp2_check
輸入：backtest/resultsV41EV/cases_input.csv（31 個台股案、燈亮月）、resultsV41EV/members.csv（代表股版、同業等權版入選成員＝peers_input_TW 前 3 名）；
     跨線信箱 附件-舊16段大漲燈1燈2月份_產業分析線-20261025-1455.csv、附件-舊15段失敗燈2月份_產業分析線-20261025-1525.csv（複本存結果夾）。
輸出 backtest/resultsAddOnLamp2/：rows.csv、cases.csv（每案×每版一列）、stats.csv、summary.md、main.json、run.log

═══ 讀法（★＝執行者定）═══
 A0 燈 1 那 1 份 ＝ resultsV41EV 同一口徑：進場＝燈亮月（cases_input）下一個月第一個交易日還原開盤；判決＝進場＋60 個月；資料不夠 ⇒ 結算到資料尾、標「未到判決日」（照 V41EV 入統計、件數照報）；
    對大盤 market_tri；R 扣 0.585% 來回；主題（案）＝1 個樣本，主題內各檔等權；代表股版與同業等權版都報。主程式自驗燈 1 那 1 份的 60 月超額＝resultsV41EV/themes.csv。
 A1 加碼月：大漲 ＝ 燈 2 月（出場表）的次月第一個交易日；失敗 ＝ 附件「加碼月」（已是燈 2 次月）第一個交易日。
    不加碼：K44（燈 2 與燈 1 同月）、K52（無燈 2）、失敗段查無 5 段（K01、K03、K13、K19、K37）、K45（買進前已綠）、K56（燈 1 延續）。
    K35（補貼驅動、v4.1 3c 本來不買）⇒ 主表整案剔除；另附「含 K35」版（加碼月 2022-04）。加碼進場須晚於燈 1 進場。每檔（代表股／各同業）加 2 份。
 A2 加碼那 2 份 ★ 兩種結算：(b) 主欄＝跟燈 1 那 1 份同一天結算（燈 1 進場＋60 月）；(a) 副欄＝自己的 60 月（加碼進場＋60 月）。報 2 份合計（＝每份超額×2）。
 A3 甲＝只買 1 份（60 月超額）；乙＝1 份＋加碼 2 份總損益（(b) 同結算日）；沒加碼的案乙＝甲；報酬率版＝乙 ÷ 投入份數（3 或 1）。壞根：主欄截斷、接續版另附。
"""
from __future__ import annotations

import json
import os
import shutil
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import researchLampCensus as LC               # noqa: E402

MB_DIR = "/mnt/c/SynologyDrive/跨線信箱/"
F_WIN = MB_DIR + "附件-舊16段大漲燈1燈2月份_產業分析線-20261025-1455.csv"
F_LOSE = MB_DIR + "附件-舊15段失敗燈2月份_產業分析線-20261025-1525.csv"
V41 = "backtest/resultsV41EV"
OUT = "backtest/resultsAddOnLamp2"
H = 60
VARS = ("代表股版", "同業等權版")
WARN = ("⚠ 事後挑的樣本（16 段大漲、15 段失敗）⇒ 只描述、⛔ 不是期望值的證據；大漲段燈 2 是早期研究標的、未照「只用當時出處」重核，失敗段有重核（寬鬆口徑），"
        "兩組口徑不同。——描述、⛔ 不判定、不計 N。")
log = LC.log
LOG = LC.LOG


def addon_plan():
    W = pd.read_csv(F_WIN, dtype=str, keep_default_na=False); L = pd.read_csv(F_LOSE, dtype=str, keep_default_na=False)
    plan = {}
    for _, r in W.iterrows():
        l1, l2 = r["燈1月_案例表"], r["燈2月_出場表"]
        if l2 in ("無", ""):
            plan[r["id"]] = (None, "無燈 2")
        elif l2 <= l1:
            plan[r["id"]] = (None, f"燈 2 {l2} 不晚於燈 1 {l1}")
        else:
            plan[r["id"]] = (l2, f"燈 2 {l2} ⇒ 次月加")         # 引擎 entry(ym) 取 ym 次月第一個交易日
    for _, r in L.iterrows():
        a = r["加碼月"]
        if a == "不加碼":
            plan[r["id"]] = (None, f"不加碼（{r['燈2月']}）")
        else:
            plan[r["id"]] = (str(pd.Period(a, "M") - 1), f"加碼月 {a}（燈 2 {r['燈2月']}）")
    return plan, W, L


def hs(v):
    v = np.asarray([x for x in v if np.isfinite(x)], float)
    if not len(v):
        return {"n": 0, "平均": np.nan, "中位": np.nan, ">0": np.nan}
    return {"n": len(v), "平均": float(v.mean()), "中位": float(np.median(v)), ">0": float((v > 0).mean())}


def main():
    t0 = time.time(); os.makedirs(OUT, exist_ok=True)
    shutil.copyfile(F_WIN, os.path.join(OUT, "win16_lamp2_input.csv")); shutil.copyfile(F_LOSE, os.path.join(OUT, "lose15_lamp2_input.csv"))
    plan, W, L = addon_plan()
    CS = pd.read_csv(os.path.join(V41, "cases_input.csv"), dtype=str, keep_default_na=False)
    CS = CS[CS["市場"] == "TW"].copy()
    if len(CS) != 31 or (CS["結果"] == "大漲").sum() != 16:
        raise SystemExit("⛔ 台股案數不符 31／16")
    if set(CS["id"]) != set(plan):
        raise SystemExit(f"⛔ 加碼表與案例表 id 不符：{set(CS['id']) ^ set(plan)}")
    # 燈 1 月份對照（附件 vs cases_input）
    mism = []
    for _, r in W.iterrows():
        c = CS[CS["id"] == r["id"]]["燈亮月"].iloc[0]
        if c != r["燈1月_案例表"]:
            mism.append(f"{r['id']} 案例表 {c} vs 附件 {r['燈1月_案例表']}")
    for _, r in L.iterrows():
        c = CS[CS["id"] == r["id"]]["燈亮月"].iloc[0]
        if c != r["燈1月"]:
            mism.append(f"{r['id']} 案例表 {c} vs 附件 {r['燈1月']}")
    MB = pd.read_csv(os.path.join(V41, "members.csv"), dtype={"代號": str})
    MB = MB[(MB["市場"] == "TW") & MB["版"].isin(VARS) & (MB["入選"].astype(str) == "True")]
    EN = LC.Engine()
    meta = {"tw_sha": EN.sha, "面板尾": str(EN.CAL[EN.CEND].date()), "燈1月不符": mism}
    ROWS = []
    pairs = MB[["id", "代號"]].drop_duplicates()
    for _, p in pairs.iterrows():
        cid, sid = p["id"], p["代號"]; c = CS[CS["id"] == cid].iloc[0]
        base = {"id": cid, "結果": c["結果"], "型": c["型"], "產業": c["產業"], "代號": sid, "燈亮月": c["燈亮月"], "加碼依據": plan[cid][1]}
        en = EN.entry(sid, c["燈亮月"])
        if en[0] is None:
            ROWS.append({**base, "段": "燈1", "狀態": en[1]}); continue
        i, e, dl = en
        tg = EN.CAL[e] + pd.DateOffset(months=H)
        ROWS.append({**base, "段": "燈1", "進場順延日": dl, **EN.settle(i, sid, e, tg)})
        ym2 = plan[cid][0]
        if ym2 is None:
            continue
        e2r = EN.entry(sid, ym2)
        if e2r[0] is None:
            ROWS.append({**base, "段": "加碼(b)", "狀態": e2r[1]}); continue
        _, e2, dl2 = e2r
        if e2 <= e:
            ROWS.append({**base, "段": "加碼(b)", "狀態": "加碼進場不晚於燈1、不加碼"}); continue
        ROWS.append({**base, "段": "加碼(b)", "進場順延日": dl2, **EN.settle(i, sid, e2, tg)})
        ROWS.append({**base, "段": "加碼(a)", "進場順延日": dl2, **EN.settle(i, sid, e2, EN.CAL[e2] + pd.DateOffset(months=H))})
    RW = pd.DataFrame(ROWS)
    cols = ["id", "結果", "型", "產業", "代號", "燈亮月", "加碼依據", "段", "進場日", "進場順延日", "目標日", "結算日", "狀態", "壞根日", "未到", "R", "大盤", "超額",
            "接續R", "接續超額", "接續結算日", "接續註", "xb"]
    RW = RW.reindex(columns=cols); RW.to_csv(os.path.join(OUT, "rows.csv"), index=False, encoding="utf-8-sig")
    # 每案×每版
    TH = pd.read_csv(os.path.join(V41, "themes.csv"), dtype=str)
    CR = []; selfchk = []
    for v in VARS:
        for _, c in CS.iterrows():
            cid = c["id"]; mem = MB[(MB["版"] == v) & (MB["id"] == cid)]["代號"].tolist()
            d = RW[(RW["id"] == cid) & RW["代號"].isin(mem) & RW["R"].notna()]
            d1 = d[d["段"] == "燈1"]
            if not len(d1):
                CR.append({"版": v, "id": cid, "結果": c["結果"], "檔數": 0}); continue
            rec = {"版": v, "id": cid, "結果": c["結果"], "型": c["型"], "產業": c["產業"], "燈亮月": c["燈亮月"], "各檔": "／".join(d1["代號"]), "檔數": len(d1),
                   "加碼依據": plan[cid][1], "甲": d1["超額"].mean(), "甲接續": d1["xb"].mean(), "燈1未到": bool(d1["未到"].astype(bool).any()),
                   "燈1截斷": bool(d1["狀態"].str.contains("壞根").any())}
            for seg, tag in (("加碼(b)", "b"), ("加碼(a)", "a")):
                q = d[d["段"] == seg]
                ok_ = len(q) == len(d1) and len(q) > 0
                rec[f"加碼{tag}"] = q["超額"].mean() if ok_ else np.nan
                rec[f"加碼{tag}接續"] = q["xb"].mean() if ok_ else np.nan
                rec[f"加碼{tag}未到"] = bool(q["未到"].astype(bool).any()) if ok_ else False
            rec["有加碼"] = bool(np.isfinite(rec["加碼b"]))
            rec["加碼進場日"] = d[d["段"] == "加碼(b)"]["進場日"].iloc[0] if rec["有加碼"] else ""
            ab = rec["加碼b"]; abx = rec["加碼b接續"]
            rec["乙"] = rec["甲"] + 2 * ab if rec["有加碼"] else rec["甲"]
            rec["乙率"] = (rec["甲"] + 2 * ab) / 3 if rec["有加碼"] else rec["甲"]
            rec["乙接續"] = rec["甲接續"] + 2 * abx if rec["有加碼"] else rec["甲接續"]
            CR.append(rec)
            t = TH[(TH["版"] == v) & (TH["市場"] == "TW") & (TH["id"] == cid) & (TH["H月"] == "60")]
            if len(t):
                selfchk.append(abs(float(t["等權超額"].iloc[0]) - rec["甲"]))
    CR = pd.DataFrame(CR); CR.to_csv(os.path.join(OUT, "cases.csv"), index=False, encoding="utf-8-sig")
    meta["自驗_燈1對V41EV_themes"] = f"{len(selfchk)} 格、最大差 {max(selfchk):.2e}"
    log(f"[自驗] 燈 1 那 1 份 60 月超額 vs resultsV41EV/themes.csv：{meta['自驗_燈1對V41EV_themes']}")
    # 統計
    ST = []
    for incl in ("主表(剔K35)", "含K35"):
        for v in VARS:
            base = CR[(CR["版"] == v) & (CR["檔數"] > 0)]
            if incl == "主表(剔K35)":
                base = base[base["id"] != "K35"]
            for grp in ("全部", "大漲", "失敗"):
                b = base if grp == "全部" else base[base["結果"] == grp]
                for lab, col, sub in (("加碼2份(b)同結算日", "加碼b", True), ("加碼2份(a)自己60月", "加碼a", True), ("加碼2份(b)接續版", "加碼b接續", True),
                                      ("甲只買1份", "甲", False), ("乙有加碼(總損益)", "乙", False), ("乙有加碼(÷投入份數)", "乙率", False),
                                      ("甲接續版", "甲接續", False), ("乙接續版", "乙接續", False)):
                    bb = b[b["有加碼"]] if sub else b
                    vals = (2 * bb[col]) if sub else bb[col]
                    ST.append({"樣本": incl, "版": v, "組": grp, "量": lab, "案數": len(b), "有加碼案": int(b["有加碼"].sum()),
                               "未到": int((bb["加碼b未到"] if sub else bb["燈1未到"]).sum()), **hs(vals.tolist())})
    ST = pd.DataFrame(ST); ST.to_csv(os.path.join(OUT, "stats.csv"), index=False, encoding="utf-8-sig")
    write_md(CR, ST, RW, meta, plan)
    MJ = {"性質": "舊 31 段燈 2 加碼測試（描述）", "警語": WARN, "請求": "產業 seq41 §三、seq42、seq43", **meta, "stats": ST.to_dict("records"),
          "讀法": __doc__.split("═══ 讀法")[1], "秒": round(time.time() - t0)}
    json.dump(MJ, open(os.path.join(OUT, "main.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1,
              default=lambda o: (None if not np.isfinite(o) else float(o)) if isinstance(o, (np.floating, np.integer, float)) else str(o))
    open(os.path.join(OUT, "run.log"), "w", encoding="utf-8").write("\n".join(LOG) + "\n")
    log(f"[完成] {OUT}｜{time.time() - t0:.0f}s")


f2 = LC.f2
pc = LC.pc


def g(ST, **kw):
    d = ST
    for a, b in kw.items():
        d = d[d[a] == b]
    return d.iloc[0]


def write_md(CR, ST, RW, meta, plan):
    md = [WARN, "", "# 舊 31 段燈 2 加碼 2 份測試（產業 seq41 §三、seq42、seq43）", "",
          "- 口徑＝resultsV41EV：燈 1 那 1 份＝燈亮月次月第一個交易日開盤進場、60 月判決（資料不夠結算到資料尾、標未到判決日、照入統計）、對大盤 market_tri 含息超額（份）、扣 0.585% 來回；"
          "案＝1 個樣本、案內各檔等權；代表股版與同業等權版（peers_input_TW 前 3 名）都報。",
          "- 加碼：燈 2 次月第一個交易日開盤每檔加 2 份。主欄 (b)＝與燈 1 那 1 份同日結算（燈 1 進場＋60 月）；副欄 (a)＝加碼自己的 60 月。報 2 份合計（每份超額×2）。",
          "- 甲＝只買 1 份；乙＝1 份＋加碼 2 份總損益（(b)）；沒加碼的案乙＝甲；報酬率版＝乙÷投入份數（3 或 1）。",
          "- K35（補貼驅動、v4.1 3c 本來不買）主表整案剔除；另附含 K35 版（加碼月 2022-04）。",
          f"- 燈 2 出現比例（產業 seq43）：大漲 14／16、失敗 7／15（主表剔 K35 後 7／14）。",
          f"- 自驗：燈 1 那 1 份 60 月超額 vs resultsV41EV/themes.csv {meta['自驗_燈1對V41EV_themes']}。燈 1 月份附件 vs 案例表不符：{('；'.join(meta['燈1月不符'])) or '無'}。",
          f"- 資料：台股面板 sha {meta['tw_sha'][:12]}（面板尾 {meta['面板尾']}）。", ""]
    for incl in ("主表(剔K35)", "含K35"):
        md += [f"## {incl}", "", "| 版 | 組 | 案數（有加碼） | 加碼 2 份 (b) 同結算日 平均／中位（＞0） | 加碼 2 份 (a) 自己 60 月 平均／中位 | 甲 平均／中位 | 乙總損益 平均／中位 | 乙÷份數 平均／中位 |",
               "|---|---|---|---|---|---|---|---|"]
        for v in VARS:
            for grp in ("大漲", "失敗", "全部"):
                b = g(ST, 樣本=incl, 版=v, 組=grp, 量="加碼2份(b)同結算日"); a = g(ST, 樣本=incl, 版=v, 組=grp, 量="加碼2份(a)自己60月")
                j = g(ST, 樣本=incl, 版=v, 組=grp, 量="甲只買1份"); y = g(ST, 樣本=incl, 版=v, 組=grp, 量="乙有加碼(總損益)"); yr = g(ST, 樣本=incl, 版=v, 組=grp, 量="乙有加碼(÷投入份數)")
                md.append(f"| {v} | {grp} | {j['n']}（{b['n']}） | {f2(b['平均'])}／{f2(b['中位'])}（{pc(b['>0'])}） | {f2(a['平均'])}／{f2(a['中位'])} | "
                          f"{f2(j['平均'])}／{f2(j['中位'])} | {f2(y['平均'])}／{f2(y['中位'])} | {f2(yr['平均'])}／{f2(yr['中位'])} |")
        md.append("")
    md += ["### 接續版（壞根改用減資／面額變更接續值；主表）", "", "| 版 | 組 | 加碼 2 份 (b) 平均／中位 | 甲 平均／中位 | 乙 平均／中位 |", "|---|---|---|---|---|"]
    for v in VARS:
        for grp in ("大漲", "失敗", "全部"):
            b = g(ST, 樣本="主表(剔K35)", 版=v, 組=grp, 量="加碼2份(b)接續版"); j = g(ST, 樣本="主表(剔K35)", 版=v, 組=grp, 量="甲接續版")
            y = g(ST, 樣本="主表(剔K35)", 版=v, 組=grp, 量="乙接續版")
            md.append(f"| {v} | {grp} | {f2(b['平均'])}／{f2(b['中位'])} | {f2(j['平均'])}／{f2(j['中位'])} | {f2(y['平均'])}／{f2(y['中位'])} |")
    ny = CR[(CR["檔數"] > 0) & (CR["燈1未到"] | CR["加碼b未到"].fillna(False).astype(bool))]
    md += ["", f"- 未到判決日（結算到資料尾）：" + ("、".join(sorted(set(f"{r['id']}" for _, r in ny.iterrows()))) or "無"),
           "- 壞根截斷：" + ("；".join(f"{r.id} {r.代號} {r.段} {r.狀態} {r.壞根日}（{r.接續註}）" for r in RW[RW["狀態"].fillna("").str.contains("壞根")].itertuples()) or "無"),
           "- 價格資料不足：" + ("；".join(f"{r.id} {r.代號}（{r.狀態}）" for r in RW[RW["R"].isna()].itertuples()) or "無"), ""]
    md += ["## 每案一列（60 月對大盤超額，份）", "", "| 版 | id | 結果 | 產業 | 燈亮月 | 各檔 | 加碼依據 | 加碼進場 | 甲 | 加碼 2 份 (b) | 加碼 2 份 (a) | 乙 | 乙÷份數 |", "|" + "---|" * 13]
    for _, r in CR[CR["檔數"] > 0].iterrows():
        md.append(f"| {r['版']} | {r['id']} | {r['結果']} | {r['產業']} | {r['燈亮月']} | {r['各檔']} | {r['加碼依據']} | {r['加碼進場日'] or '—'} | {f2(r['甲'])}{'（未到）' if r['燈1未到'] else ''} | "
                  f"{f2(2 * r['加碼b']) if r['有加碼'] else '—'} | {f2(2 * r['加碼a']) if r['有加碼'] else '—'} | {f2(r['乙'])} | {f2(r['乙率'])} |")
    md += ["", WARN]
    open(os.path.join(OUT, "summary.md"), "w", encoding="utf-8").write("\n".join(md) + "\n")


if __name__ == "__main__":
    main()

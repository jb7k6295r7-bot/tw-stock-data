# -*- coding: utf-8 -*-
"""現金增資、可轉債公告後偏弱 seq2【事件層描述・正式跑】（台股策略線 登錄 sha bdf021608239a93d，2026-10-21 00:20；裁定 seq385 第三題、seq388 發號、
seq411 §三 核 seq2、seq412 §四 核准開正式跑：可判；3 年確認段 n_eff 19／16 只描述）；Loughran & Ritter 1995、可轉債 Spiess & Affleck-Graves 1999——回測線計算子代理。
避開名單的事件層描述（N 不計）；⛔ 不當選股、⛔ 不當營量／營飆濾網。
⛔ 不 commit、不改既有程式與結果夾（resultsSEO/freq 不動）；researchSEO_freq（讀法 S1～S10 寫死、沿用；load_events、dedup12、prior12、xsec）、
   researchIndMom（共用：exright 版、出場、統計）⛔ 只 import。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchSEO [--procs 2]
    對帳：PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchSEO_check
輸出 backtest/resultsSEO/（⛔ 不碰 freq/）：SEO.json、SEO_表.csv、by_year.csv、events.csv.gz（逐筆事件、配對、R、X）、block_ci.csv、
     recon_freq.csv、exright_diff.csv、先驗.csv、run.log

═══ 讀法（S 標續編；頻率表 S1～S10 原樣沿用，以下為正式跑新增；⛔ 在讀任何本件報酬之前寫死於 2026-10-21（台北）；★＝執行者定，〔 〕內為另一讀法）═══
 S11 資料快照 ＝ 頻率表當時的 origin/main b5532121f8d8（seo_cb_events、stocks.csv；唯讀）；價格面板 ＝ 頻率表同一份快取。
     exright 版（裁定 seq412 §三）＝ researchIndMom I11 同一份：正式跑全程（前 12 個月報酬的壞根、進場剔除、配對公司可買、出場壞根）用 exright 版；
     另用舊口徑照 S1～S8 逐列重建 freq/events.csv.gz（sid、date、組、st、世界、T、e、走完旗標、配對類別、主池／放寬池候選數），任一不同 ⇒ 中止、⛔ 不算報酬；
     exright 版不同的列照報。
 S12 配對（登錄 §二）：主池（S8：非發行 ∧ 同市值十分位 ∧ 同前 12 個月報酬五分位）依 |市值 − 發行公司市值| 由小到大（★ 同距離依代號），
     取第一家「e 進場保留」（exright 版：(T,e] 無壞根、e 有成交、開盤有效、非開盤鎖漲停）者；主池無可買 ⇒ 放寬池同法；兩池都無可買 ⇒ 配對失敗（照報）。
     ★ 同一家配對公司用於 6 個月／1 年／3 年三種持有。配對因「最近者不可買」而改用次近者的筆數照報。
 S13 持有：進場 e ＝ 公告日下一交易日開盤（S3）；出場 ＝ ★ e 日期 ＋ H 個曆月（DateOffset）當天或之前最後一個交易日收盤（＝ S6「走完」同一把尺）；
     H ＝ 12（主）、36（並報）、6（描述）。逐股出場規則 ＝ researchIndMom I13（壞根前一根強制、持有中下市 ⇒ 下市前最後收盤、到期無成交用前一根）；
     出場日超出主世界資料尾 ⇒ 不可算（只收走完）。★ 早年事件出場日跨 2014-12-31 接縫 ⇒「接縫不明」不收（筆數照報；早年只描述）。
     R ＝ 出場還原收盤 ÷ e 還原開盤 − 1；量 X ＝ R事件 − R配對（登錄「扣 0.585%」兩邊同扣、抵銷；淨 R 另欄）。配對公司 R 不可算 ⇒ 該筆該 H 不收（照報）。
 S14 判定（登錄 §三，描述）：CI ＝ 公告月分群（research11.cl_stats；key ＝ 公告日 date 的年月）1.96；n_eff ＝ min(筆數, 公告月數) ＜ 30 ⇒ 依構造不可判定；
     30～99 ⇒「樣本中等」；② ＝ 下界 ＞ 0、③ ＝ 上界 ＜ 0、① ＝ 含 0。⭐「避開名單成立」＝ S、C 各自 1 年 探索、確認 兩段都 ③（seq388）。
     ★ Bonferroni 2 組（S、C；Φ⁻¹(1−0.05/4)＝2.2414）並報，與 1.96 不同 ⇒ 照寫。3 年：確認段 n_eff 19／16（頻率表）⇒ 只描述、不判（seq412）；
     探索段 3 年照列（並報）。登錄未列假訊號臂 ⇒ 本件不判 seq322（照寫；本件為避開名單描述、N 不計）。
 S15 描述：C國內、C海外、S私、C私（只描述、⛔ 不入成立判斷）、6 個月、早年 2005～2016（上櫃 2007-07 起）；12 個月不重疊區塊重抽 CI
     （公告月起每 12 個曆月一塊、10,000 次、種子 [20261022, 段序, 組序]）；配對類別（主／放寬）分開的 X̄；S、C 同日兩組都算的重疊筆數（引頻率表 S10）。
 S16 結果句必附：「描述，不是選股規則」「原文持有 5 年、台股主看 1 年」「可轉債出處為 Spiess & Affleck-Graves 1999，非 L&R」「單筆層通過 ≠ 組合會贏 0050」；
     早年附 researchTurtle.NOTE_EARLY；本件不用月營收 ⇒ 不附存活者句；事件表人工抽查 94% 正確、已知殘留誤收照報（資料庫 1021-0009）。
     同根兩出場價取較低（seq373）：每筆只有一種出場價 ⇒ 不適用，照寫。重大訊息類別短期反應（seq303）不重判。
 S17 先驗（登錄 §七）判讀 ★：① S 組 1 年兩段皆 ③；② C 組 1 年主全窗（探索＋確認合併）X̄ ＜ 0；③ 探索段（3 年可判的唯一段）S、C 合併 3 年 X̄ ＜ 1 年 X̄。
"""
from __future__ import annotations

import argparse
import gzip
import json
import os
import sys
import time
from collections import Counter, defaultdict
from statistics import NormalDist

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import researchSEO_freq as SQ                 # noqa: E402  頻率表（⛔ 只 import）
from backtest import researchIndMom_freq as IM              # noqa: E402
from backtest import researchIndMom as IMX                  # noqa: E402  共用（⛔ 只 import）
from backtest import researchIndRev_prereg as PRE           # noqa: E402  okcode
from backtest import research11 as R                        # noqa: E402
from backtest import researchTurtle as TU                   # noqa: E402

REG_SHA = SQ.REG_SHA
PIN_SHA = "b5532121f8d8d18e52328cae2345cd56220289d0"
OUT = "backtest/resultsSEO"
FREQ_DIR = SQ.OUT
COST = IMX.COST
Z196 = 1.96
ZB2 = NormalDist().inv_cdf(1 - 0.05 / 4)
HS = (6, 12, 36)
GROUPS = ("S", "C", "C國內", "C海外", "S私", "C私")
SEGS = SQ.SEGS
SEAM = pd.Timestamp("2014-12-31")
SENT = ["描述，不是選股規則", "原文持有 5 年、台股主看 1 年", "可轉債出處為 Spiess & Affleck-Graves 1999，非 L&R", "單筆層通過 ≠ 組合會贏 0050"]
LOG = IM.LOG
log = IM.log
pct = IMX.pct
CMP = ["sid", "date", "time", "組", "海外", "market", "已下市", "st", "世界", "T", "e", "6月走完", "1年走完", "3年走完", "前後3年窗截到表尾", "配對",
       "主池候選數", "放寬池候選數"]


def build_rows(Zs, IX, ev_, keep, alive, iss, tail_ev, main_tail, memo, want_lists=False):
    """S1～S8 原樣（researchSEO_freq.main 迴圈逐行照抄；Zs 可為舊口徑或 exright 版）；want_lists ⇒ 另回配對候選清單（依市值距離排序）。"""
    def issued_near(s, lo, hi):
        v = iss.get(s)
        if v is None:
            return False
        k = np.searchsorted(v, lo, "left")
        return k < len(v) and v[k] <= hi
    rows = []
    for k, r in ev_.iterrows():
        s, d, g = r["stock_id"], r["d"], r["組"]
        row = {"sid": s, "date": str(d.date()), "time": r["time"], "組": g, "海外": bool(r["海外"]), "market": r["market"], "已下市": s not in alive,
               "st": "", "世界": "", "T": "", "e": ""}
        if not keep[k]:
            row["st"] = "12個月內重複略過"; rows.append(row); continue
        if not PRE.okcode(s):
            row["st"] = "非四碼普通股"; rows.append(row); continue
        wn = None
        for w in ("早年", "主"):
            cal = Zs[w]["cal"]
            pe = int(cal.searchsorted(d, side="right"))
            if pe < len(cal) and (w == "主" or cal[pe] <= pd.Timestamp("2014-12-31")):
                wn = w; break
        if wn is None:
            row["st"] = "超出資料尾"; rows.append(row); continue
        Z = Zs[wn]; cal = Z["cal"]
        e = int(cal.searchsorted(d, side="right")); T = int(cal.searchsorted(d, side="right")) - 1
        if T < 0:
            row["st"] = "早於價格資料" if wn == "早年" else "跨世界接縫"; rows.append(row); continue
        row.update({"世界": wn, "T": str(cal[T].date()), "e": str(cal[e].date())})
        i = IX[wn].get(s)
        if i is None:
            row["st"] = "不在面板(gate3／不足260根)"; rows.append(row); continue
        if not (Z["G"][i, T] and np.isfinite(Z["C"][i, T])):
            row["st"] = "閘外(500張/pit/T無K棒)"; rows.append(row); continue
        row["st"] = IM.entry_flag(Z, i, T, e)
        ed = cal[e]
        for nmh, mo in (("6月走完", 6), ("1年走完", 12), ("3年走完", 36)):
            row[nmh] = bool(ed + pd.DateOffset(months=mo) <= main_tail)
        row["前後3年窗截到表尾"] = bool(d + pd.DateOffset(years=3) > tail_ev)
        out, qm, qr = SQ.xsec(Z, T, memo[wn])
        if int(i) not in out or qm is None:
            row["配對"] = "配對不可算"
        else:
            mc0, r0 = out[int(i)]
            dm = int(np.searchsorted(qm, mc0, "right")); dr = int(np.searchsorted(qr, r0, "right"))
            lo = np.datetime64(d - pd.DateOffset(years=3)); hi = np.datetime64(d + pd.DateOffset(years=3))
            non = {j for j in out if not issued_near(Z["sids"][j], lo, hi)}
            same_d = [j for j in non if j != i and int(np.searchsorted(qm, out[j][0], "right")) == dm]
            prim = [j for j in same_d if int(np.searchsorted(qr, out[j][1], "right")) == dr]
            row["主池候選數"] = len(prim); row["放寬池候選數"] = len(same_d)
            row["配對"] = "主配對" if prim else ("放寬配對" if same_d else "配對失敗")
            if want_lists:
                key = lambda j: (abs(out[j][0] - mc0), Z["sids"][j])
                row["_prim"] = sorted(prim, key=key); row["_rel"] = sorted(same_d, key=key)
                row["_i"] = int(i); row["_T"] = T; row["_e"] = e
        rows.append(row)
    return rows


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--procs", type=int, default=2)
    a = ap.parse_args()
    t0 = time.time()
    os.makedirs(OUT, exist_ok=True)
    reg = IM.reg_check(REG_SHA)
    log(f"[登錄] {reg}（sha {REG_SHA} 已驗）")
    DATA = IMX.pinned_data(PIN_SHA)
    log(f"[資料] 頻率表快照 {PIN_SHA[:12]} ⇒ {DATA}")
    ev = SQ.load_events(DATA)
    tail_ev = ev["d"].max()
    st_ = pd.read_csv(os.path.join(DATA, "meta", "stocks.csv"), dtype=str)
    ls = pd.to_datetime(st_["last_seen"], errors="coerce"); alive = set(st_.loc[ls >= ls.max() - pd.Timedelta(days=10), "stock_id"])
    Zo, Zx, EXD = {}, {}, []
    for wn in ("早年", "主"):
        Zo[wn] = IMX.aux2(IM.panel_aux(IM.build_panel(wn, a.procs)))
        X = IMX.build_exr(Zo[wn], a.procs)
        Zx[wn] = IMX.make_x(Zo[wn], X)
    IX = {wn: {s: i for i, s in enumerate(Z["sids"])} for wn, Z in Zo.items()}
    main_tail = Zo["主"]["cal"][-1]
    iss = defaultdict(list)
    for s, d in zip(ev["stock_id"], ev["d"]):
        iss[s].append(d)
    iss = {s: np.array(sorted(v), dtype="datetime64[ns]") for s, v in iss.items()}
    ev_ = ev[ev["ipo"] == 0].reset_index(drop=True)
    keep = SQ.dedup12(ev_)
    # ── S11 舊口徑重建 ⇒ 與頻率表逐列比
    rows_o = build_rows(Zo, IX, ev_, keep, alive, iss, tail_ev, main_tail, {"早年": {}, "主": {}})
    Eo = pd.DataFrame(rows_o)
    Ef = pd.read_csv(os.path.join(FREQ_DIR, "events.csv.gz"), dtype=str, keep_default_na=False)
    RECON = []
    nbad = 0
    if len(Ef) != len(Eo):
        raise SystemExit(f"⛔ 頻率表 events 列數 {len(Ef)} ≠ 重建 {len(Eo)}")
    for c in CMP:
        a_ = Ef[c].astype(str).to_numpy() if c in Ef else np.array([""] * len(Ef))
        b_ = Eo[c].map(lambda v: "" if (v is None or (isinstance(v, float) and np.isnan(v))) else (str(int(v)) if isinstance(v, float) and float(v).is_integer() else str(v))).to_numpy() if c in Eo else np.array([""] * len(Eo))
        a2 = np.array([x[:-2] if x.endswith(".0") else x for x in a_])
        diff = int((a2 != b_).sum())
        RECON.append({"欄": c, "不同列數": diff})
        nbad += diff
    if nbad:
        raise SystemExit(f"⛔ 頻率表 events 逐列重建不同：{[r for r in RECON if r['不同列數']]} ⇒ 中止、不算報酬")
    log(f"[S11] 頻率表 events 逐列重建：{len(Eo)} 列 × {len(CMP)} 欄全同｜{time.time() - t0:.0f}s")
    # ── exright 版
    rows_x = build_rows(Zx, IX, ev_, keep, alive, iss, tail_ev, main_tail, {"早年": {}, "主": {}}, want_lists=True)
    Ex = pd.DataFrame(rows_x)
    for k in range(len(Eo)):
        for c in ("st", "配對", "主池候選數", "放寬池候選數"):
            vo, vx = rows_o[k].get(c), rows_x[k].get(c)
            if str(vo) != str(vx):
                EXD.append({"sid": rows_o[k]["sid"], "date": rows_o[k]["date"], "組": rows_o[k]["組"], "欄": c, "舊": vo, "新": vx})
    log(f"[S11] exright 版與舊口徑不同 {len(EXD)} 處｜{time.time() - t0:.0f}s")
    # ── S12～S13 配對與報酬
    OUTR = []
    for k, r in Ex.iterrows():
        if r["st"] != "保留":
            continue
        wn = r["世界"]; Z = Zx[wn]; cal = Z["cal"]; n0 = len(cal)
        rec = {"sid": r["sid"], "date": r["date"], "組": r["組"], "海外": r["海外"], "世界": wn, "e": r["e"], "公告月": r["date"][:7], "已下市": r["已下市"],
               "配對類別(頻率表)": r["配對"]}
        e = int(cal.searchsorted(pd.Timestamp(r["e"]))); T = e - 1                     # S3：e ＝ d 之後第一個交易日、T ＝ e 前一個
        ie = IX[wn][r["sid"]]
        m = None; used = "配對失敗"; skipped = 0
        if r["配對"] in ("主配對", "放寬配對"):
            for nmp, lst in (("主配對", r["_prim"]), ("放寬配對", r["_rel"])):
                for j in lst:
                    if IM.entry_flag(Z, int(j), T, e) == "保留":
                        m = int(j); used = nmp; break
                    skipped += 1
                if m is not None:
                    break
        elif r["配對"] == "配對不可算":
            used = "配對不可算"
        rec.update({"配對實際": used, "配對公司": Z["sids"][m] if m is not None else "", "配對略過不可買": skipped})
        ed = cal[e]
        for H in HS:
            tgt = ed + pd.DateOffset(months=H)
            if wn == "早年" and tgt > SEAM:
                rec[f"H{H}"] = "接縫不明"; continue
            if tgt > cal[-1]:
                rec[f"H{H}"] = "超出資料尾"; continue
            x = int(cal.searchsorted(tgt, side="right")) - 1
            exe, Re, te = IMX.exits_vec(Z, np.array([ie]), e, x)
            rec[f"R{H}"] = float(Re[0]); rec[f"出場{H}"] = IMX.TYPN[int(te[0])]
            if m is None:
                rec[f"H{H}"] = "無配對"; continue
            exm, Rm, tm = IMX.exits_vec(Z, np.array([m]), e, x)
            if not (np.isfinite(Re[0]) and np.isfinite(Rm[0])):
                rec[f"H{H}"] = "R不可算"; continue
            rec[f"H{H}"] = "ok"; rec[f"R配對{H}"] = float(Rm[0]); rec[f"X{H}"] = float(Re[0] - Rm[0]); rec[f"配對出場{H}"] = IMX.TYPN[int(tm[0])]
        OUTR.append(rec)
    EV = pd.DataFrame(OUTR)
    log(f"[報酬] 保留事件 {len(EV)}｜配對實際 {dict(Counter(EV['配對實際']))}｜{time.time() - t0:.0f}s")
    # ── 統計
    TAB = []; BLK = []
    gsel = {"S": EV["組"] == "S", "C": EV["組"] == "C", "C國內": (EV["組"] == "C") & ~EV["海外"].astype(bool),
            "C海外": (EV["組"] == "C") & EV["海外"].astype(bool), "S私": EV["組"] == "S私", "C私": EV["組"] == "C私"}
    edt = pd.to_datetime(EV["e"])
    for sg, (x_, y_) in list(SEGS.items()) + [("主全窗(參考)", ("2017-03-02", None))]:
        x_ = pd.Timestamp(x_); y_ = main_tail if y_ is None else pd.Timestamp(y_)
        insg = (edt >= x_) & (edt <= y_)
        for g in GROUPS:
            for H in HS:
                sub = EV[gsel[g] & insg & (EV.get(f"H{H}") == "ok")]
                st = IMX.stats(sub[f"X{H}"] if len(sub) else [], sub["公告月"] if len(sub) else [], zj=Z196, zb=ZB2)
                judged = (g in ("S", "C") and H == 12 and sg in ("探索", "確認"))
                role = "判定(描述)" if judged else ("並報" if (g in ("S", "C") and H == 36 and sg == "探索") else "描述")
                if g in ("S", "C") and H == 36 and sg == "確認":
                    role = "只描述(seq412：n_eff 19／16)"
                row = {"段": sg, "組": g, "H": H, "身分": role, **{k: st.get(k) for k in ("n", "群數", "n_eff", "樣本", "X̄", "中位", "X勝率", "lo", "hi", "結果", "t",
                                                                                     "bonf_lo", "bonf_hi")}}
                if st.get("n", 0):
                    row["結果_Bonf2"] = IMX.res_of(st["bonf_lo"], st["bonf_hi"], st["n_eff"])
                    row["R̄事件"] = float(sub[f"R{H}"].mean()); row["R̄配對"] = float(sub[f"R配對{H}"].mean()); row["淨R̄事件"] = float(sub[f"R{H}"].mean() - COST)
                    row["已下市比例"] = float(sub["已下市"].astype(bool).mean())
                    row["持有中下市筆數"] = int((sub[f"出場{H}"] == "下市末根").sum()); row["壞根強制筆數"] = int((sub[f"出場{H}"] == "壞根前一根強制").sum())
                    row["放寬配對比例"] = float((sub["配對實際"] == "放寬配對").mean())
                    for cat in ("主配對", "放寬配對"):
                        q = sub[sub["配對實際"] == cat]
                        row[f"X̄_{cat}"] = float(q[f"X{H}"].mean()) if len(q) else None
                    if H == 12 and sg != "主全窗(參考)":
                        bk = IMX.block_ci(sub[f"X{H}"], sub["公告月"], 12, [20261022, list(SEGS).index(sg), GROUPS.index(g)])
                        row["區塊CI"] = f"[{pct(bk.get('lo'))}, {pct(bk.get('hi'))}] {bk.get('結果')}"
                        row["區塊CI較寬"] = bool(bk.get("結果") != st.get("結果")) if st.get("結果") != "依構造不可判定" else None
                        BLK.append({"段": sg, "組": g, **bk})
                # 不可收的原因
                allg = EV[gsel[g] & insg]
                row["不收原因"] = json.dumps({k: int(v) for k, v in Counter(allg.get(f"H{H}", pd.Series(dtype=str)).fillna("—")).items() if k != "ok"}, ensure_ascii=False)
                TAB.append(row)
    TB = pd.DataFrame(TAB)
    jd = TB[TB["身分"] == "判定(描述)"].set_index(["組", "段"])
    ok_list = {g: bool((jd.loc[g]["結果"] == "結果③").all()) for g in ("S", "C")}

    def word(r):
        return {"結果②": "好", "結果③": "差", "結果①": "分不出"}.get(r, "依構造不可判定")
    sents = {}
    for g, nm in (("S", "董事會決議現金增資"), ("C", "董事會決議發可轉債")):
        a1, b1 = jd.loc[(g, "探索")], jd.loc[(g, "確認")]
        same = "兩段一致" if a1["結果"] == b1["結果"] else "兩段不一致"
        sents[g] = (f"{nm}的公司，之後 1 年比同規模、同前期漲幅的公司：探索段{word(a1['結果'])} {pct(a1['X̄'])}（{a1['樣本']}）、確認段{word(b1['結果'])} "
                    f"{pct(b1['X̄'])}（{b1['樣本']}）（{same}）")
    # 先驗
    mg = TB[(TB["段"] == "主全窗(參考)") & (TB["組"] == "C") & (TB["H"] == 12)].iloc[0]
    ex_ = EV[(edt >= pd.Timestamp("2017-03-02")) & (edt <= pd.Timestamp("2021-12-30")) & EV["組"].isin(["S", "C"])]
    x1 = ex_.loc[ex_["H12"] == "ok", "X12"].mean(); x3 = ex_.loc[ex_["H36"] == "ok", "X36"].mean()
    PRIOR = [{"先驗": "① 現增組 1 年兩段皆 ③（約三成五）", "中": ok_list["S"], "實際": f"探索 {jd.loc[('S', '探索'), '結果']}｜確認 {jd.loc[('S', '確認'), '結果']}"},
             {"先驗": "② 可轉債組 1 年 X ＜ 0 方向（約五成五）", "中": bool(mg["X̄"] < 0), "實際": f"主全窗 C 1 年 X̄ {pct(mg['X̄'])}；探索 {pct(jd.loc[('C', '探索'), 'X̄'])}｜確認 {pct(jd.loc[('C', '確認'), 'X̄'])}"},
             {"先驗": "③ 3 年版的 X 比 1 年更負（約五成五）", "中": bool(x3 < x1), "實際": f"探索段 S＋C：3 年 {pct(x3)} vs 1 年 {pct(x1)}"}]
    BY = EV.assign(年=EV["date"].str[:4]).groupby(["組", "年"]).agg(n=("sid", "size"), X12̄=("X12", "mean"), n12=("X12", "count")).reset_index()
    eqf = pd.read_csv(os.path.join(FREQ_DIR, "equiv.csv")).to_dict("records")
    J = {"性質": "現增／可轉債公告後 seq2 事件層描述正式跑（N 不計）", "登錄": f"台股策略線 seq2 sha {REG_SHA}",
         "裁定": "seq385 第三題、seq388、seq411 §三、seq412 §四（3 年確認段只描述）", "資料": {"快照": PIN_SHA},
         "判定": TB[TB["身分"] == "判定(描述)"].to_dict("records"), "避開名單成立": ok_list, "結果句": sents, "必附": SENT,
         "早年附註": TU.NOTE_EARLY, "先驗": PRIOR, "先驗中": sum(1 for p in PRIOR if p["中"]), "S_vs_C等價(引頻率表)": eqf,
         "頻率表重建": RECON, "exright差異": EXD, "配對實際": dict(Counter(EV["配對實際"])),
         "配對略過不可買(筆)": int((EV["配對略過不可買"] > 0).sum()), "seq322": "登錄未列假訊號臂 ⇒ 不判（避開名單描述、N 不計）",
         "seq373": "同根兩出場價取較低：每筆只有一種出場價 ⇒ 不適用，照寫", "讀法": __doc__.split("═══ 讀法")[1],
         "時間": pd.Timestamp.now(tz="Asia/Taipei").strftime("%Y-%m-%d %H:%M")}
    TB.to_csv(os.path.join(OUT, "SEO_表.csv"), index=False, encoding="utf-8-sig")
    BY.to_csv(os.path.join(OUT, "by_year.csv"), index=False, encoding="utf-8-sig")
    with gzip.open(os.path.join(OUT, "events.csv.gz"), "wt", encoding="utf-8") as fh:
        EV.to_csv(fh, index=False)
    pd.DataFrame(BLK).to_csv(os.path.join(OUT, "block_ci.csv"), index=False, encoding="utf-8-sig")
    pd.DataFrame(RECON).to_csv(os.path.join(OUT, "recon_freq.csv"), index=False, encoding="utf-8-sig")
    pd.DataFrame(EXD, columns=["sid", "date", "組", "欄", "舊", "新"]).to_csv(os.path.join(OUT, "exright_diff.csv"), index=False, encoding="utf-8-sig")
    pd.DataFrame(PRIOR).to_csv(os.path.join(OUT, "先驗.csv"), index=False, encoding="utf-8-sig")
    json.dump(J, open(os.path.join(OUT, "SEO.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    for g in sents:
        log(f"[結果] {sents[g]}")
    log(f"[避開名單成立] {ok_list}")
    log(f"[完] {time.time() - t0:.0f}s")
    open(os.path.join(OUT, "run.log"), "w", encoding="utf-8").write("\n".join(LOG) + "\n")


if __name__ == "__main__":
    main()

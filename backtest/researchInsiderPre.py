# -*- coding: utf-8 -*-
"""董監／大股東申報轉讓後偏弱 seq2【事件層描述・正式跑】（台股策略線 登錄 sha 3e8056296f03d825，2026-10-21 00:20；裁定 seq407 第三題、seq408 發號、
seq412 §六 准開頻率表、seq416 §三 核准正式跑；Seyhun 1986、Lakonishok & Lee 2001）——回測線計算子代理。
避開名單的事件層描述（N 不計，seq407）；⛔ 不當選股、⛔ 不當濾網；結果句 ⛔ 不寫成賣出／放空建議。
⛔ 不 commit、不改既有程式與結果夾（resultsInsiderPre/freq 不動）；researchInsiderPre_freq（讀法 Q1～Q13 寫死、沿用；norm_group、plan_shares、
   combined_cal、SharesOut）、researchSEO_freq（xsec）、researchIndMom_freq（面板、entry_flag）、researchIndMom（exright 版、exits_vec、stats、block_ci）⛔ 只 import。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchInsiderPre
    對帳：PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchInsiderPre_check
輸出 backtest/resultsInsiderPre/（⛔ 不碰 freq/）：InsiderPre.json、InsiderPre_表.csv、prior3_diff.csv、先驗.csv、events.csv.gz（逐筆事件、配對、R、X；
     ⛔ 無姓名、無 holder_key）、block_ci.csv、recon_freq.csv、exright_diff.csv、by_year.csv、run.log

═══ 讀法（Q 標續編；頻率表 Q1～Q13 原樣沿用（seq416 §三：拆組順序、錨點式合併、占比分母、配對不推翻），以下為正式跑新增；
    ⛔ 在讀任何本件報酬之前寫死於 2026-10-21（台北）；★＝執行者定，〔 〕內為另一讀法）═══
 Q14 資料快照 ＝ 頻率表當時的 origin/main dbfb96cb81a7（~/b2fwork/ipf_main_dbfb96cb81a7，唯讀；⛔ 不 merge main、⛔ 不用之後的 main）；
     價格面板 ＝ 頻率表同一份快取 ~/b2fwork/panel_<世界>.pkl；exright 表 ＝ researchIndMom I11 同一份（origin/main b5532121f8d8，三件共用）。
     ⭐ 頻率表對帳：本檔以舊口徑（＝頻率表）照 Q1～Q10 同式重建 freq/events.csv.gz 全部列、全部欄（含配對代號、主池候選數、占比），
     任一不同 ⇒ 中止、⛔ 不算報酬。
 Q15 exright 版（裁定 seq412 §三：新件 open_base 一律 exright 版）：正式跑全程（前 12 個月報酬的壞根、進場剔除、配對公司可買、出場壞根）用 exright 版；
     與舊口徑不同的列（st、配對、主池候選數、配對代號）照報 exright_diff.csv。
 Q16 配對（登錄 §二；Q10 池原樣）：主池依 |log 市值比| 由小到大（★ 同距離依代號）取第一家「e 進場保留」（exright 版：(T,e] 無壞根、e 有成交、
     開盤有效、非開盤鎖漲停）者 ★〔頻率表只取最近者、不看可買〕；池內無可買 ⇒ 配對失敗（照報）。最近者不可買而改用次近者的筆數照報。
     ★ 同一家配對公司用於 20／60／250 日三種持有。
 Q17 持有（登錄 §二「持有 20／60／250 個交易日」）：進場 e ＝ 申報日下一交易日開盤（Q5）；★ 出場目標 x ＝ e ＋ H − 1（e 所在世界日曆；e 當天算第 1 天，
     Long3 L12／PTH R2 同式）收盤。逐股出場 ＝ researchIndMom I13（exits_vec：(e, x] 有壞根 ⇒ 第一個壞根前一根收盤強制；持有中下市 ⇒ 末根收盤；
     x 無成交 ⇒ 之前最後一根）。★ 早年世界事件 x 超出早年日曆（2014-12-31 接縫）⇒「接縫不明」不收（早年只描述；筆數照報）；
     ★ 只收頻率表「H 日走完」旗標為真者（＝頻率表 n_eff 同口徑；未走完照報）。
     R ＝ 出場還原收盤 ÷ e 還原開盤 − 1；量 X ＝ R事件 − R配對（登錄未寫成本；兩邊同扣、抵銷 ⇒ X 不扣）。配對公司 R 不可算 ⇒ 該筆該 H 不收（照報）。
 Q18 判定（登錄 §三，描述）：判定格 ＝ 一般交易組、60 日、探索／確認 各判（依 e 歸段，Q7）。X̄ 申報月分群 CI（research11.cl_stats 式；key ＝ 事件首筆申報日年月）；
     ★ Bonferroni 族 N ＝ 1（本登錄判定只有「一般交易 60 日」1 格；兩段是「且」不是兩格）⇒ z ＝ 1.96；另並報 z ＝ 2.2414（若把先驗③ 也算 1 格 ⇒ N＝2），
     兩者不同 ⇒ 照寫。n_eff ＝ min(事件數, 申報月數) ＜ 30 ⇒ 依構造不可判定；30～99 ⇒「樣本中等」；② ＝ 下界 ＞ 0、③ ＝ 上界 ＜ 0、① ＝ 含 0。
     ⭐「避開名單成立」＝ 兩段都 ③（seq407）。登錄未列假訊號臂 ⇒ 不做、不判 seq322（照寫）。
 Q19 描述（⛔ 不判；seq416 §三）：贈與、信託、其他（混合組依構造為空）、20／250 日、身分（董監、經理人、大股東；一事件可屬多類，Q8）、
     占比 ≥ 1%／＜ 1%（Q9 分母不推翻）；贈與 ≥ 1% 子組「依構造不可判定」（n_eff ＜ 30 ⇒ stats 自動標）；早年 2003-05～2016-12（上櫃 2007-07 起）；
     H 日不重疊區塊重抽 CI（申報月由第一個事件月起每 B 個曆月一塊，B ＝ 20 日:1、60 日:3、250 日:12 ★；10,000 次；種子 [20261022, 段序, 組序, H]），
     與月分群結果不同 ⇒「區塊 CI 較寬」。主全窗（探索＋確認）照列參考。
 Q20 先驗③（seq416：可判）：一般交易組 60 日，差 ＝ X̄(占比 ≥ 1%) − X̄(占比 ＜ 1%)；★ 差的 CI ＝ 申報月分群（cl_stats 同式 CR0：
     ψ ＝ (x − m₁)/n₁（≥1%）、−(x − m₀)/n₀（＜1%），se ＝ √Σ_月(Σψ)²），z ＝ 1.96；n_eff ＝ min(兩子組各自 n_eff)。
     ★ 先驗③「中」＝ 探索、確認兩段的差 CI 上界皆 ＜ 0；差的點估計方向另報。
     先驗①「中」＝ 判定格兩段皆 ③；先驗② ★「中」＝ 贈與組 60 日 探索、確認 兩段皆 ①（與配對分不出）。
 Q21 限制員工信託移組（seq416 §三）：照「判不出、不移組」（Q2；資料庫 transferee_type 先判信託／銀行），結果句照寫。
 Q22 一般交易約四成多事後未完成轉讓（seq416 §三）：⛔ 不篩；事件層「未完成」＝ 事件內任一列 unfinished＝是 ★（另報列層比例），結果句必附
     「申報要賣近半最後沒賣完」。
 Q23 結果句必附：「描述，不是選股規則」「贈與、信託不算賣出、另組」「台股文獻只讀到摘要」「單筆層通過 ≠ 組合會贏 0050」「申報要賣近半最後沒賣完」
     「受讓人為限制員工信託者判不出、未移出信託組」；早年附 researchTurtle.NOTE_EARLY（reduce_v2，早年含減資假飆股約 0.3%）。
     同根兩出場價取較低（seq373）：每筆只有一種出場價（固定持有期收盤／壞根前一根收盤／下市末根互斥）⇒ 不適用，照寫。
     控制組定義用到申報日後 60 個交易日內的申報（登錄原文「前後 60 個交易日」）⇒ 只影響配對公司選擇、不影響事件訊號；照寫。
"""
from __future__ import annotations

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
from backtest import researchInsiderPre_freq as Q           # noqa: E402  頻率表（⛔ 只 import）
from backtest import researchIndMom_freq as IM              # noqa: E402
from backtest import researchIndMom as IMX                  # noqa: E402  exright、exits_vec、stats、block_ci（⛔ 只 import）
from backtest import researchSEO_freq as SQ                 # noqa: E402  xsec
from backtest import researchIndRev_prereg as PRE           # noqa: E402  okcode
from backtest import researchTurtle as TU                   # noqa: E402  NOTE_EARLY

REG_SHA = Q.REG_SHA
PIN_SHA = "dbfb96cb81a7d3032e07fe47d1aeb5f0230545fa"
OUT = "backtest/resultsInsiderPre"
FREQ_DIR = Q.OUT
Z196 = 1.96
ZB2 = NormalDist().inv_cdf(1 - 0.05 / 4)
HS = Q.HOLDS
GROUPS = Q.GROUPS
SEGS = Q.SEGS
BMON = {20: 1, 60: 3, 250: 12}
SUBS = ("全部", "董監", "經理人", "大股東", "占比≥1%", "占比<1%")
SENT = ["描述，不是選股規則", "贈與、信託不算賣出、另組", "台股文獻只讀到摘要", "單筆層通過 ≠ 組合會贏 0050", "申報要賣近半最後沒賣完",
        "受讓人為限制員工信託者判不出、未移出信託組（seq416 §三）"]
SENT_373 = "同根兩出場價取較低（seq373）：每筆只有一種出場價（固定持有期收盤／壞根前一根收盤／下市末根互斥）⇒ 不適用，照寫"
LOG = IM.LOG
log = IM.log
pct = IMX.pct
CMP = ["sid", "date", "組", "market", "已下市", "列數", "申報日數", "末筆", "董監", "經理人", "大股東", "其他身分", "預定股數", "首日預定股數", "st", "世界",
       "T", "e", "已發行股數", "占比", "首日占比", "20日走完", "20日跨世界", "60日走完", "60日跨世界", "250日走完", "250日跨世界", "配對", "±60窗截到表尾",
       "非申報檔數", "主池候選數", "配對代號", "|log市值比|", "申報月", "年"]


def pinned_data():
    root = os.path.join(IM.WORK, f"ipf_main_{PIN_SHA[:12]}")
    if not os.path.isfile(os.path.join(root, ".done")) or open(os.path.join(root, ".done")).read().strip() != PIN_SHA:
        raise SystemExit(f"⛔ 頻率表資料快照 {root} 不存在或 sha 不符")
    return os.path.join(root, "data")


def prep(DATA, Zs):
    """Q1～Q4、Q11（頻率表 main 前段逐行照抄）。"""
    X = Q.load_rows(DATA)
    st = pd.read_csv(os.path.join(DATA, "meta", "stocks.csv"), dtype=str)
    ls = pd.to_datetime(st["last_seen"], errors="coerce"); alive = set(st.loc[ls >= ls.max() - pd.Timedelta(days=10), "stock_id"])
    CAL = Q.combined_cal(Zs); NC = len(CAL)
    ng = [Q.norm_group(m, t, o) for m, t, o in zip(X["method_raw"], X["transferee_type"], X["transferee_org"])]
    X["組"] = [g for g, _ in ng]; X["信託轉其他"] = [f for _, f in ng]
    X["身分"] = X["role"].map(Q.role_class); X["分項"] = X["role"].map(Q.role_sub)
    X["受託旗標"] = X["role"].str.contains("由受託人持有"); X["子公司"] = X["role"].str.startswith("子公司")
    ps = [Q.plan_shares(r, g) for r, g in zip(X.to_dict("records"), X["組"])]
    X["預定股數"] = [v for v, _ in ps]; X["改用plan"] = [f for _, f in ps]
    orig_cols = [c for c in X.columns if c not in ("d", "組", "信託轉其他", "身分", "分項", "受託旗標", "子公司", "預定股數", "改用plan")]
    X["完全重複"] = X.duplicated(subset=orig_cols, keep="first")
    X["p"] = CAL.searchsorted(X["d"], side="right") - 1
    Y = X[X["market"].isin(["sii", "otc"])].copy()
    Y = Y.sort_values(["組", "stock_id", "d", "market"], kind="mergesort").reset_index()
    evs = []; cur = None
    for k, r in enumerate(Y.itertuples(index=False)):
        key = (r.組, r.stock_id)
        if cur is None or cur["key"] != key or r.p - cur["p0"] > Q.MERGE_TD:
            if cur is not None:
                evs.append(cur)
            cur = {"key": key, "p0": int(r.p), "d": r.d, "market": r.market, "rows": []}
        cur["rows"].append(k)
    if cur is not None:
        evs.append(cur)
    allsid = sorted(set(X["stock_id"]) | set(Zs["早年"]["sids"]) | set(Zs["主"]["sids"]))
    SR = {s: k for k, s in enumerate(allsid)}
    DM = np.zeros((len(allsid), NC + 1), np.int32)
    for s, p in zip(X["stock_id"], X["p"]):
        if p >= 0:
            DM[SR[s], p + 1] += 1
    CS = np.cumsum(DM, axis=1)
    return X, Y, evs, alive, CAL, SR, CS


def build_rows(Zs, IX, Y, evs, alive, CAL, SR, CS, SO, want_lists=False, logf=None):
    """Q5～Q10（頻率表 main 迴圈逐行照抄；Zs 可為舊口徑或 exright 版）；want_lists ⇒ 另回主池候選（依 |log 市值比|、代號排序）。"""
    logf = logf or log
    NC = len(CAL)
    main_tail = Zs["主"]["cal"][-1]; main_tail_pos = int(CAL.searchsorted(main_tail))
    early_last_pos = int(CAL.searchsorted(Zs["早年"]["cal"][-1]))
    memo = {"早年": {}, "主": {}}; memo2 = {"早年": {}, "主": {}}
    t0 = time.time()

    def xs_arrays(wn, Z, T):
        if T not in memo2[wn]:
            out, qm, qr = SQ.xsec(Z, T, memo[wn])
            js = np.array(sorted(out), int)
            mc = np.array([out[j][0] for j in js]); rr = np.array([out[j][1] for j in js])
            qi = np.searchsorted(qr, rr, "right") if qr is not None else None
            rows = np.array([SR[Z["sids"][j]] for j in js], int)
            memo2[wn][T] = (out, qr, js, mc, qi, rows)
        return memo2[wn][T]

    recs = []
    for n_, ev in enumerate(evs):
        g, s = ev["key"]; d = ev["d"]
        R_ = Y.loc[ev["rows"]]
        nd = R_[~R_["完全重複"]]
        cls = set(R_["身分"])
        rec = {"sid": s, "date": str(d.date()), "組": g, "market": ev["market"], "已下市": s not in alive, "列數": len(R_),
               "申報日數": int(R_["d"].nunique()), "末筆": str(R_["d"].max().date()),
               "董監": "董監" in cls, "經理人": "經理人" in cls, "大股東": "大股東" in cls, "其他身分": "其他身分" in cls,
               "預定股數": float(nd["預定股數"].sum(min_count=1)) if nd["預定股數"].notna().any() else np.nan,
               "首日預定股數": float(nd.loc[nd["d"] == d, "預定股數"].sum(min_count=1)) if nd.loc[nd["d"] == d, "預定股數"].notna().any() else np.nan,
               "st": "", "世界": "", "T": "", "e": ""}
        # 正式跑新增（不入對帳）：未完成旗標（Q22）
        rec["_未完成任一列"] = bool((R_["unfinished"] == "是").any()); rec["_未完成列比例"] = float((R_["unfinished"] == "是").mean())
        recs.append(rec)
        if not PRE.okcode(s):
            rec["st"] = "非四碼普通股"; continue
        wn = None
        for w in ("早年", "主"):
            cal = Zs[w]["cal"]
            pe = int(cal.searchsorted(d, side="right"))
            if pe < len(cal) and (w == "主" or cal[pe] <= pd.Timestamp("2014-12-31")):
                wn = w; break
        if wn is None:
            rec["st"] = "超出資料尾"; continue
        Z = Zs[wn]; cal = Z["cal"]
        e = int(cal.searchsorted(d, side="right")); T = e - 1
        if T < 0:
            rec["st"] = "早於價格資料" if wn == "早年" else "跨世界接縫"; continue
        rec.update({"世界": wn, "T": str(cal[T].date()), "e": str(cal[e].date())})
        so = SO.get(wn, s, cal[T])
        rec["已發行股數"] = so
        rec["占比"] = rec["預定股數"] / so if (np.isfinite(so) and so > 0 and np.isfinite(rec["預定股數"])) else np.nan
        rec["首日占比"] = rec["首日預定股數"] / so if (np.isfinite(so) and so > 0 and np.isfinite(rec["首日預定股數"])) else np.nan
        if wn == "早年" and ev["market"] == "otc" and cal[T] < Q.OTC_EARLY:
            rec["st"] = "上櫃早於2007-07無股價"; continue
        i = IX[wn].get(s)
        if i is None:
            rec["st"] = "不在面板(gate3／不足260根)"; continue
        if not (Z["G"][i, T] and np.isfinite(Z["C"][i, T])):
            rec["st"] = "閘外(500張/pit/T無K棒)"; continue
        rec["st"] = IM.entry_flag(Z, i, T, e)
        if want_lists:
            rec["_i"] = int(i); rec["_T"] = T; rec["_e"] = e
        pe_c = int(CAL.searchsorted(cal[e])); pT_c = int(CAL.searchsorted(cal[T]))
        for h in HS:
            rec[f"{h}日走完"] = bool(pe_c + h <= main_tail_pos)
            rec[f"{h}日跨世界"] = bool(wn == "早年" and pe_c + h > early_last_pos)
        if rec["st"] != "保留":
            continue
        out, qr, js, mc, qi, rows = xs_arrays(wn, Z, T)
        if int(i) not in out or qr is None:
            rec["配對"] = "配對不可算"; continue
        mc0, r0 = out[int(i)]; q0 = int(np.searchsorted(qr, r0, "right"))
        lo = max(pT_c - Q.CTRL_TD, 0); hi = pT_c + Q.CTRL_TD
        rec["±60窗截到表尾"] = bool(hi > NC - 1)
        hi = min(hi, NC - 1)
        decl = (CS[rows, hi + 1] - CS[rows, lo]) > 0
        ok = (~decl) & (qi == q0) & (js != int(i))
        rec["非申報檔數"] = int((~decl).sum()); rec["主池候選數"] = int(ok.sum())
        if ok.any():
            lr = np.abs(np.log(mc[ok] / mc0)); k = int(np.argmin(lr))
            rec["配對"] = "主配對"; rec["配對代號"] = Z["sids"][int(js[ok][k])]; rec["|log市值比|"] = float(lr[k])
            if want_lists:
                jj = js[ok]; ss = np.array([Z["sids"][int(j)] for j in jj])
                order = np.lexsort((ss, lr))
                rec["_pool"] = [int(j) for j in jj[order]]; rec["_lr"] = [float(v) for v in lr[order]]
        else:
            rec["配對"] = "配對失敗"
        if (n_ + 1) % 5000 == 0:
            logf(f"  事件 … {n_ + 1}／{len(evs)}｜{time.time() - t0:.0f}s")
    E = pd.DataFrame(recs)
    E["申報月"] = E["date"].str[:7]
    E["年"] = E["date"].str[:4].astype(int)
    return E


def _s(v):
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return ""
    if isinstance(v, (bool, np.bool_)):
        return str(bool(v))
    if isinstance(v, (float, np.floating)):
        return repr(float(v))
    return str(v)


def recon(Ef, Eo):
    """逐列逐欄比（數值欄以 float 比、容差 0；字串欄完全相同）。"""
    out = []; nbad = 0
    if len(Ef) != len(Eo):
        raise SystemExit(f"⛔ 頻率表 events 列數 {len(Ef)} ≠ 重建 {len(Eo)}")
    for c in CMP:
        a = Ef[c].to_numpy() if c in Ef else np.array([""] * len(Ef))
        b = Eo[c].to_numpy() if c in Eo else np.array([None] * len(Eo))
        diff = 0
        for x, y in zip(a, b):
            ys = _s(y)
            if x == ys:
                continue
            try:
                if x != "" and ys != "" and float(x) == float(ys):
                    continue
            except ValueError:
                pass
            diff += 1
        out.append({"欄": c, "不同列數": diff}); nbad += diff
    return out, nbad


def diff_ci(x, big, key, z=Z196):
    """Q20：X̄(big) − X̄(¬big) 與申報月分群 CR0 se。"""
    x = np.asarray(x, float); big = np.asarray(big, bool); key = np.asarray(key)
    ok = np.isfinite(x); x, big, key = x[ok], big[ok], key[ok]
    n1, n0 = int(big.sum()), int((~big).sum())
    if n1 == 0 or n0 == 0:
        return {"n≥1%": n1, "n<1%": n0}
    m1, m0 = float(x[big].mean()), float(x[~big].mean())
    psi = np.where(big, (x - m1) / n1, -(x - m0) / n0)
    se = float(np.sqrt((pd.Series(psi).groupby(key).sum().to_numpy() ** 2).sum()))
    ne1 = min(n1, len(set(key[big]))); ne0 = min(n0, len(set(key[~big])))
    ne = min(ne1, ne0); dd = m1 - m0
    return {"n≥1%": n1, "n<1%": n0, "n_eff≥1%": ne1, "n_eff<1%": ne0, "n_eff": ne, "X̄≥1%": m1, "X̄<1%": m0, "差": dd, "se": se,
            "lo": dd - z * se, "hi": dd + z * se, "結果": IMX.res_of(dd - z * se, dd + z * se, ne), "方向": "≥1% 較負" if dd < 0 else "≥1% 不較負"}


def main():
    t0 = time.time()
    os.makedirs(OUT, exist_ok=True)
    reg = IM.reg_check(REG_SHA)
    log(f"[登錄] {reg}（sha {REG_SHA} 已驗）")
    DATA = pinned_data()
    log(f"[資料] 頻率表快照 {PIN_SHA[:12]} ⇒ {DATA}")
    Zo, Zx = {}, {}
    for wn in ("早年", "主"):
        Zo[wn] = IMX.aux2(IM.panel_aux(IM.build_panel(wn, 2)))
        Xr = IMX.build_exr(Zo[wn], 2)
        Zx[wn] = IMX.make_x(Zo[wn], Xr)
    IX = {wn: {s: i for i, s in enumerate(Z["sids"])} for wn, Z in Zo.items()}
    X, Y, evs, alive, CAL, SR, CS = prep(DATA, Zo)
    log(f"[事件表] {len(X)} 列｜上市櫃 {len(Y)} 列 ⇒ {len(evs)} 事件")
    sids_early = {Y.loc[e["rows"][0], "stock_id"] for e in evs if e["d"] <= pd.Timestamp("2015-01-31")}
    SO = Q.SharesOut(Zo, sids_early)
    # ── Q14 舊口徑重建 ⇒ 與頻率表逐列比
    Eo = build_rows(Zo, IX, Y, evs, alive, CAL, SR, CS, SO)
    Ef = pd.read_csv(os.path.join(FREQ_DIR, "events.csv.gz"), dtype=str, keep_default_na=False)
    RECON, nbad = recon(Ef, Eo)
    pd.DataFrame(RECON).to_csv(os.path.join(OUT, "recon_freq.csv"), index=False, encoding="utf-8-sig")
    if nbad:
        raise SystemExit(f"⛔ 頻率表 events 逐列重建不同：{[r for r in RECON if r['不同列數']]} ⇒ 中止、不算報酬")
    log(f"[Q14] 頻率表 events 逐列重建：{len(Eo)} 列 × {len(CMP)} 欄全同｜{time.time() - t0:.0f}s")
    # ── Q15 exright 版
    Ex = build_rows(Zx, IX, Y, evs, alive, CAL, SR, CS, SO, want_lists=True)
    EXD = []
    for k in range(len(Eo)):
        for c in ("st", "配對", "主池候選數", "配對代號"):
            vo, vx = _s(Eo.at[k, c]) if c in Eo else "", _s(Ex.at[k, c]) if c in Ex else ""
            if vo != vx:
                EXD.append({"sid": Eo.at[k, "sid"], "date": Eo.at[k, "date"], "組": Eo.at[k, "組"], "欄": c, "舊": vo, "新": vx})
    log(f"[Q15] exright 版與舊口徑不同 {len(EXD)} 處（{dict(Counter(d['欄'] for d in EXD))}）｜{time.time() - t0:.0f}s")
    analyze(Ex, Zo, Zx, Y, EXD, RECON, t0, OUT)


def analyze(Ex, Zo, Zx, Y, EXD, RECON, t0, OUT):
    # ── Q16～Q17 配對與報酬
    OUTR = []
    for k, r in Ex.iterrows():
        if r["st"] != "保留":
            continue
        wn = r["世界"]; Z = Zx[wn]; cal = Z["cal"]; n0 = len(cal)
        e = int(r["_e"]); T = int(r["_T"]); ie = int(r["_i"])
        rec = {"sid": r["sid"], "date": r["date"], "組": r["組"], "market": r["market"], "世界": wn, "T": r["T"], "e": r["e"], "申報月": r["申報月"],
               "已下市": r["已下市"], "董監": r["董監"], "經理人": r["經理人"], "大股東": r["大股東"], "其他身分": r["其他身分"],
               "占比": r["占比"], "未完成任一列": r["_未完成任一列"], "未完成列比例": r["_未完成列比例"], "配對(頻率表式)": r["配對"]}
        m = None; skipped = 0
        pool = r["_pool"] if isinstance(r.get("_pool"), list) else []
        for j in pool:
            if IM.entry_flag(Z, int(j), T, e) == "保留":
                m = int(j); break
            skipped += 1
        used = "主配對" if m is not None else ("配對不可算" if r["配對"] == "配對不可算" else "配對失敗")
        rec.update({"配對實際": used, "配對公司": Z["sids"][m] if m is not None else "", "配對略過不可買": skipped,
                    "|log市值比|實際": r["_lr"][skipped] if m is not None else np.nan})
        for H in HS:
            x = e + H - 1
            if not bool(r[f"{H}日走完"]):
                rec[f"H{H}"] = "未走完(頻率表口徑)"; continue
            if x > n0 - 1:
                rec[f"H{H}"] = "接縫不明" if wn == "早年" else "超出資料尾"; continue
            _, Re, te = IMX.exits_vec(Z, np.array([ie]), e, x)
            rec[f"R{H}"] = float(Re[0]); rec[f"出場{H}"] = IMX.TYPN[int(te[0])]
            if m is None:
                rec[f"H{H}"] = "無配對"; continue
            _, Rm, tm = IMX.exits_vec(Z, np.array([m]), e, x)
            if not (np.isfinite(Re[0]) and np.isfinite(Rm[0])):
                rec[f"H{H}"] = "R不可算"; continue
            rec[f"H{H}"] = "ok"; rec[f"R配對{H}"] = float(Rm[0]); rec[f"X{H}"] = float(Re[0] - Rm[0]); rec[f"配對出場{H}"] = IMX.TYPN[int(tm[0])]
        OUTR.append(rec)
    EV = pd.DataFrame(OUTR)
    log(f"[報酬] 保留事件 {len(EV)}｜配對實際 {dict(Counter(EV['配對實際']))}｜{time.time() - t0:.0f}s")
    # ── 統計
    main_tail = Zo["主"]["cal"][-1]
    edt = pd.to_datetime(EV["e"])
    TAB = []; BLK = []
    SG = list(SEGS.items()) + [("主全窗(參考)", ("2017-03-01", None))]
    for si, (sg, (x_, y_)) in enumerate(SG):
        x_ = pd.Timestamp(x_); y_ = main_tail if y_ is None else pd.Timestamp(y_)
        insg = (edt >= x_) & (edt <= y_)
        for gi, g in enumerate(GROUPS):
            for H in HS:
                for sub_ in SUBS:
                    base = EV[insg & (EV["組"] == g)]
                    if sub_ in ("董監", "經理人", "大股東"):
                        base = base[base[sub_].astype(bool)]
                    elif sub_ == "占比≥1%":
                        base = base[base["占比"] >= 0.01]
                    elif sub_ == "占比<1%":
                        base = base[base["占比"] < 0.01]
                    sub = base[base.get(f"H{H}", pd.Series(index=base.index, dtype=object)) == "ok"] if len(base) else base
                    st = IMX.stats(sub[f"X{H}"] if len(sub) else [], sub["申報月"] if len(sub) else [], zj=Z196, zb=ZB2)
                    judged = (g == "一般交易" and H == 60 and sub_ == "全部" and sg in ("探索", "確認"))
                    row = {"段": sg, "組": g, "H": H, "子組": sub_, "身分": "判定(描述)" if judged else "描述",
                           **{k: st.get(k) for k in ("n", "群數", "n_eff", "樣本", "X̄", "中位", "X勝率", "lo", "hi", "結果", "t", "bonf_lo", "bonf_hi")}}
                    if st.get("n", 0):
                        row["結果_Bonf2"] = IMX.res_of(st["bonf_lo"], st["bonf_hi"], st["n_eff"])
                        row["R̄事件"] = float(sub[f"R{H}"].mean()); row["R̄配對"] = float(sub[f"R配對{H}"].mean())
                        row["已下市比例"] = float(sub["已下市"].astype(bool).mean())
                        row["持有中下市筆數"] = int((sub[f"出場{H}"] == "下市末根").sum()); row["壞根強制筆數"] = int((sub[f"出場{H}"] == "壞根前一根強制").sum())
                        row["配對下市末根筆數"] = int((sub[f"配對出場{H}"] == "下市末根").sum())
                        row["未完成事件比例"] = float(sub["未完成任一列"].astype(bool).mean())
                        if sub_ == "全部" and sg != "主全窗(參考)":
                            bk = IMX.block_ci(sub[f"X{H}"], sub["申報月"], BMON[H], [20261022, si, gi, H])
                            row["區塊CI"] = f"[{pct(bk.get('lo'))}, {pct(bk.get('hi'))}] {bk.get('結果')}"
                            row["區塊CI較寬"] = bool(bk.get("結果") != st.get("結果")) if st.get("結果") != "依構造不可判定" else None
                            BLK.append({"段": sg, "組": g, "H": H, **bk})
                    row["不收原因"] = json.dumps({kk: int(v) for kk, v in Counter(base.get(f"H{H}", pd.Series(dtype=str)).fillna("—")).items() if kk != "ok"},
                                             ensure_ascii=False)
                    TAB.append(row)
    TB = pd.DataFrame(TAB)
    jd = TB[TB["身分"] == "判定(描述)"].set_index("段")
    ok_avoid = bool((jd["結果"] == "結果③").all())
    # Q20 先驗③
    P3 = []
    for sg, (x_, y_) in SG:
        x_ = pd.Timestamp(x_); y_ = main_tail if y_ is None else pd.Timestamp(y_)
        s = EV[(edt >= x_) & (edt <= y_) & (EV["組"] == "一般交易") & (EV.get("H60") == "ok") & np.isfinite(EV["占比"].astype(float))]
        dc = diff_ci(s["X60"], s["占比"] >= 0.01, s["申報月"])
        dcb = diff_ci(s["X60"], s["占比"] >= 0.01, s["申報月"], z=ZB2)
        P3.append({"段": sg, **dc, "lo_Bonf2": dcb.get("lo"), "hi_Bonf2": dcb.get("hi"), "結果_Bonf2": dcb.get("結果")})
    P3d = pd.DataFrame(P3).set_index("段")

    def word(r):
        return {"結果②": "好", "結果③": "差", "結果①": "分不出"}.get(r, "依構造不可判定")
    a1, b1 = jd.loc["探索"], jd.loc["確認"]
    same = "兩段一致" if a1["結果"] == b1["結果"] else "兩段不一致"
    unf = EV[(EV["組"] == "一般交易") & (edt >= pd.Timestamp("2017-03-01"))]
    unf_ev = float(unf["未完成任一列"].astype(bool).mean())
    sent = (f"董監／大股東申報一般交易轉讓後 60 天，比同規模、同前期漲幅的公司：探索段{word(a1['結果'])} {pct(a1['X̄'])}"
            f"（n {int(a1['n'])}、n_eff {int(a1['n_eff'])}，{a1['樣本']}）、確認段{word(b1['結果'])} {pct(b1['X̄'])}（n {int(b1['n'])}、n_eff {int(b1['n_eff'])}，"
            f"{b1['樣本']}）（{same}）；避開名單{'成立' if ok_avoid else '不成立'}")
    gift = TB[(TB["組"] == "贈與") & (TB["H"] == 60) & (TB["子組"] == "全部")].set_index("段")
    PRIOR = [{"先驗": "① 一般交易組兩段皆 ③（約三成）", "中": ok_avoid, "實際": f"探索 {a1['結果']}｜確認 {b1['結果']}"},
             {"先驗": "② 贈與組與配對無差（約七成）", "中": bool((gift.loc["探索", "結果"] == "結果①") and (gift.loc["確認", "結果"] == "結果①")),
              "實際": f"贈與 60 日 探索 {gift.loc['探索', '結果']} {pct(gift.loc['探索', 'X̄'])}｜確認 {gift.loc['確認', '結果']} {pct(gift.loc['確認', 'X̄'])}"},
             {"先驗": "③ 申報股數占比 ≥ 1% 的組 X 比 ＜ 1% 更負（約五成五）",
              "中": bool(P3d.loc["探索", "hi"] < 0 and P3d.loc["確認", "hi"] < 0),
              "實際": f"差(≥1%−<1%) 探索 {pct(P3d.loc['探索', '差'])} [{pct(P3d.loc['探索', 'lo'])}, {pct(P3d.loc['探索', 'hi'])}] {P3d.loc['探索', '結果']}｜"
                      f"確認 {pct(P3d.loc['確認', '差'])} [{pct(P3d.loc['確認', 'lo'])}, {pct(P3d.loc['確認', 'hi'])}] {P3d.loc['確認', '結果']}｜"
                      f"點估計方向 探索 {P3d.loc['探索', '方向']}、確認 {P3d.loc['確認', '方向']}"}]
    BY = EV.assign(年=EV["date"].str[:4]).groupby(["組", "年"]).agg(n=("sid", "size"), X60̄=("X60", "mean"), n60=("X60", "count")).reset_index()
    # 未完成（列層，上市櫃一般交易）
    yg = Y[Y["組"] == "一般交易"]
    J = {"性質": "董監大股東申報轉讓後 seq2 事件層描述正式跑（避開名單、N 不計）", "登錄": f"台股策略線 seq2 sha {REG_SHA}",
         "裁定": "seq407 第三題、seq408、seq412 §六、seq416 §三", "資料": {"快照": PIN_SHA, "exright": IMX.EXR_SHA},
         "判定": TB[TB["身分"] == "判定(描述)"].to_dict("records"), "避開名單成立": ok_avoid, "結果句": sent, "必附": SENT,
         "早年附註": TU.NOTE_EARLY, "先驗": PRIOR, "先驗中": sum(1 for p in PRIOR if p["中"]), "先驗③差": P3,
         "未完成": {"一般交易保留事件(主全窗)任一列未完成": unf_ev, "上市櫃一般交易列層 unfinished＝是": float((yg["unfinished"] == "是").mean()),
                  "各段事件層": {sg: float(EV[(EV["組"] == "一般交易") & (edt >= pd.Timestamp(x)) & (edt <= (main_tail if y is None else pd.Timestamp(y)))]["未完成任一列"].astype(bool).mean())
                             for sg, (x, y) in SEGS.items()}},
         "頻率表重建": RECON, "exright差異數": dict(Counter(d["欄"] for d in EXD)), "配對實際": dict(Counter(EV["配對實際"])),
         "配對略過不可買(筆)": int((EV["配對略過不可買"] > 0).sum()), "Bonferroni": "族 N＝1 ⇒ z 1.96；並報 z 2.2414（N＝2）",
         "seq322": "登錄未列假訊號臂 ⇒ 不做、不判", "seq373": SENT_373, "限制員工": "判不出、不移組（seq416 §三）",
         "讀法": __doc__.split("═══ 讀法")[1], "時間": pd.Timestamp.now(tz="Asia/Taipei").strftime("%Y-%m-%d %H:%M")}
    TB.to_csv(os.path.join(OUT, "InsiderPre_表.csv"), index=False, encoding="utf-8-sig")
    pd.DataFrame(P3).to_csv(os.path.join(OUT, "prior3_diff.csv"), index=False, encoding="utf-8-sig")
    BY.to_csv(os.path.join(OUT, "by_year.csv"), index=False, encoding="utf-8-sig")
    with gzip.open(os.path.join(OUT, "events.csv.gz"), "wt", encoding="utf-8") as fh:
        EV.to_csv(fh, index=False)
    pd.DataFrame(BLK).to_csv(os.path.join(OUT, "block_ci.csv"), index=False, encoding="utf-8-sig")
    pd.DataFrame(EXD, columns=["sid", "date", "組", "欄", "舊", "新"]).to_csv(os.path.join(OUT, "exright_diff.csv"), index=False, encoding="utf-8-sig")
    pd.DataFrame(PRIOR).to_csv(os.path.join(OUT, "先驗.csv"), index=False, encoding="utf-8-sig")
    json.dump(J, open(os.path.join(OUT, "InsiderPre.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    log(f"[結果] {sent}")
    for p in PRIOR:
        log(f"[先驗] {p['先驗']}：{'中' if p['中'] else '不中'}｜{p['實際']}")
    log(f"[完] {time.time() - t0:.0f}s")
    open(os.path.join(OUT, "run.log"), "w", encoding="utf-8").write("\n".join(LOG) + "\n")


if __name__ == "__main__":
    main()

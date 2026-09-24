"""PREREGC3 主程式 —— 回測線執行端（⛔ 判準／出口逐字沿用 C1 形狀，⛔ 本支只跑與報、不寫解讀）。

✅ 授權：裁定線 20260924-1908「三件收下 ⇒ C3 可以開跑；六條實作選擇全照准」
⭐ 開跑前先跑 selftest_researchc3（fixture ＋ 鑑別力 ＋ 餵資料層 ＋ C1 交叉）⇒ 不綠就停
⚠ 本支另有兩條【登錄沒逐字寫到】的讀法，標在報告「實作」欄（⛔ 只影響描述欄，⛔ 不影響主判定）：
   (vii)  必報③ 隨機選幣的「每期」＝ 每一段 membership 不變的區間；區間起點重抽 |S_t| 個幣
   (viii) 描述對照② 固定六等分 ＝ 每日各 1/6 的逐幣 C1 規則（含 C1 成本）淨報酬平均
"""
from __future__ import annotations

import hashlib
import os
import subprocess
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17"))
from backtest import researchc1 as C1   # noqa: E402
from backtest import researchc3 as C3   # noqa: E402

OUT = C3.OUT
COSTS = (0.001, 0.002, 0.004, 0.008)     # §六⑤ 來回
N_NULL = 1000                            # §2-C③／§六③④
SEED = C1.SEED


def perf(r):
    return C1.cagr(r), C1.mdd(r)


def seg_shuffle(col, rng):
    segs = C1.segments(col)
    order = rng.permutation(len(segs))
    return np.concatenate([np.full(segs[k][1], segs[k][0]) for k in order])


def intervals(sig):
    """membership 不變的區間 [(起, 迄)]（迄為開區間）。"""
    T = len(sig)
    b = [0] + [t for t in range(1, T) if (sig[t] != sig[t - 1]).any()] + [T]
    return [(b[i], b[i + 1]) for i in range(len(b) - 1)]


def main():
    t0 = time.time()
    log = lambda x: print(x, flush=True)
    r = subprocess.run([sys.executable, "-m", "backtest.selftest_researchc3"], cwd=os.path.expanduser("~/tw-p17"),
                       capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stdout[-3000:]); print(r.stderr[-2000:])
        raise SystemExit("⛔⛔ C3 自測沒過 ⇒ 停止，⛔ 不出任何結果")
    log("[自測] ✅ 全綠")

    dates, close, sig, w0s = C3.load_panel()
    assert dates[0] == "2021-02-26" and dates[-1] == C1.LAST_FULL and len(dates) == 2032
    T, K = close.shape
    years = (T - 1) / C1.DAYS_YEAR

    # ── 主格 ──
    nav, st = C3.simulate(close, sig, C3.COST_RT, stats=True)
    rs = C3.rets_from_nav(nav)
    nav_b = (close / close[0]).mean(axis=1)            # 基準①：期初各 1/6、買進持有（⛔ 不扣成本，同 C1；實作 (vi)）
    rb = nav_b[1:] / nav_b[:-1] - 1.0
    cg_s, md_s = perf(rs); cg_b, md_b = perf(rb)
    ok, sc, sm = C1.judge(cg_s, md_s, cg_b, md_b)
    L = C1.politis_white_block(rs - rb)
    ci1 = C1.paired_ci(rs, rb, L, np.random.default_rng(SEED))
    ci2 = C1.paired_ci(rs, rb, 2 * L, np.random.default_rng(SEED))
    ex, why = C1.exit_of(ok, sc, sm, ci1, ci2["mdd"])
    expo = 1.0 - st["cash_frac"][:-1]                  # 第 i 期持有的曝險（收盤 i 交易後）
    n_chg = len(intervals(sig)) - 1
    log("[主格] 策略 {:+.2%}／{:.2%}　基準① {:+.2%}／{:.2%}　{}　{}｜L={}".format(
        cg_s, md_s, cg_b, md_b, "判定格過" if ok else "判定格未過", ex, L))

    # ── §四④／§五：假訊號組（逐幣整段重排 ⇒ 重合成組合）──
    degen = []
    if expo.mean() >= C1.EXPO_DEGEN:
        degen.append("平均曝險 {:.1%} ≥ 90%".format(expo.mean()))
    if n_chg < C1.MIN_TRADES:
        degen.append("membership 變動 {} 次 < 5".format(n_chg))
    rng = np.random.default_rng(SEED)
    pl = []
    for i in range(N_NULL):
        s2 = np.column_stack([seg_shuffle(sig[:, k], rng) for k in range(K)])
        pl.append(perf(C3.rets_from_nav(C3.simulate(close, s2, C3.COST_RT))))
    pl = np.array(pl)
    plc_c = float((pl[:, 0] < cg_s).mean() * 100); plc_m = float((np.abs(pl[:, 1]) > abs(md_s)).mean() * 100)
    log("[假訊號／時序打亂] CAGR 百分位 {:.1f}、|MDD| 淺於 {:.1f}%（{:.0f}s）".format(plc_c, plc_m, time.time() - t0))

    # ── §六③ 隨機選幣（橫斷面打亂；實作 (vii)）──
    rng = np.random.default_rng(SEED + 1)
    iv = intervals(sig); nin = sig.sum(axis=1).astype(int)
    rn = []
    for i in range(N_NULL):
        s3 = np.zeros_like(sig)
        for a, b in iv:
            k = nin[a]
            if k:
                s3[a:b, rng.choice(K, size=k, replace=False)] = 1.0
        rn.append(perf(C3.rets_from_nav(C3.simulate(close, s3, C3.COST_RT))))
    rn = np.array(rn)
    rnd_c = float((rn[:, 0] < cg_s).mean() * 100); rnd_m = float((np.abs(rn[:, 1]) > abs(md_s)).mean() * 100)
    log("[隨機選幣] CAGR 百分位 {:.1f}、|MDD| 淺於 {:.1f}%（{:.0f}s）".format(rnd_c, rnd_m, time.time() - t0))

    # ── §六⑤ 成本敏感度 ＋ §五之二 損益兩平成本 ──
    sens = []
    for c in COSTS:
        rc = C3.rets_from_nav(C3.simulate(close, sig, c))
        a, m = perf(rc); o, x1, x2 = C1.judge(a, m, cg_b, md_b)
        sens.append({"cost_rt": c, "cagr": a, "mdd": m, "pass": o, "strict_cagr": x1, "strict_mdd": x2})

    def strict_at(c, leg):
        a, m = perf(C3.rets_from_nav(C3.simulate(close, sig, c)))
        return a > cg_b if leg == "CAGR" else abs(m) < abs(md_b)

    def breakeven(leg):
        lo, hi = C3.COST_RT, 0.50
        if not strict_at(lo, leg):
            return float("nan")
        if strict_at(hi, leg):
            return float("inf")
        for _ in range(40):
            mid = (lo + hi) / 2
            lo, hi = (mid, hi) if strict_at(mid, leg) else (lo, mid)
        return (lo + hi) / 2
    be_c = breakeven("CAGR") if sc else float("nan")
    be_m = breakeven("MDD") if sm else float("nan")

    # ── 現金對照臂：基準① × 策略實際曝險（現金 0%）──
    rd = expo * rb
    cg_d, md_d = perf(rd)
    # ── 描述對照②：固定六等分的逐幣 C1 規則（實作 (viii)）──
    fix = []
    for k, s in enumerate(C3.COINS):
        d = pd.read_csv(os.path.join(C1.DATA, s + ".csv"), dtype={"date": str}).drop_duplicates("date").sort_values("date")
        c = d["close"].to_numpy(float); dd = d["date"].to_numpy()
        res = C1.rule_series(c, C1.N_MAIN)
        i0 = int(np.flatnonzero(dd[res["w0"]:] == dates[0])[0])
        seg = res["r_rule"][i0:i0 + T - 1]
        assert len(seg) == T - 1
        fix.append(seg)
    rf = np.mean(fix, axis=0); cg_f, md_f = perf(rf)

    # ── 必報① 持有區間 ＋ ② 換手與成本 ──
    lens = np.array([b - a for a, b in iv])
    mean_nav = float(nav.mean())
    turn = (st["buy"] + st["sell"]) / 2 / mean_nav / years
    fee_y = st["fee"] / mean_nav / years

    sha = lambda a: hashlib.sha256(np.asarray(a, float).tobytes()).hexdigest()[:16]
    os.makedirs(OUT, exist_ok=True)
    pd.DataFrame({"date": dates[1:], "r_strat": rs, "r_bench": rb, "r_cashdil": rd, "r_fix6": rf,
                  "expo": expo}).to_csv(os.path.join(OUT, "daily.csv"), index=False)
    pd.DataFrame(pl, columns=["cagr", "mdd"]).to_csv(os.path.join(OUT, "null_time.csv.gz"), index=False)
    pd.DataFrame(rn, columns=["cagr", "mdd"]).to_csv(os.path.join(OUT, "null_cross.csv.gz"), index=False)
    pd.DataFrame(sens).to_csv(os.path.join(OUT, "cost_sens.csv"), index=False)
    R = dict(cg_s=cg_s, md_s=md_s, cg_b=cg_b, md_b=md_b, ok=ok, sc=sc, sm=sm, L=L, ci1=ci1, ci2=ci2, ex=ex, why=why,
             degen=degen, plc_c=plc_c, plc_m=plc_m, rnd_c=rnd_c, rnd_m=rnd_m, sens=sens, be_c=be_c, be_m=be_m,
             cg_d=cg_d, md_d=md_d, cg_f=cg_f, md_f=md_f, lens=lens, turn=turn, fee_y=fee_y, st=st, expo=expo,
             n_chg=n_chg, T=T, years=years, sha_s=sha(rs), sha_b=sha(rb), pl=pl, rn=rn, dates=dates)
    write_report(R)
    log("[完成] {:.0f}s".format(time.time() - t0))


def write_report(R):
    p = lambda x: "{:+.2%}".format(x)
    q = lambda x: "{:.2%}".format(x)
    L = []; A = L.append
    A("# PREREGC3 交件：六幣組合層（membership 觸發、現金限制下的漂移權重）\n")
    A("⛔ 判準／出口逐字沿用登錄 v4（sha f4021ef34db9e27d）與 C1 形狀；⛔ 本檔【不寫解讀、不寫結案措辭】（那是加密策略線的格子）")
    A("⛔ 本批三件（C2／C3／C4）結算前：本件即使判定格通過，也只能寫「單件通過，本批三件結算前不宣布」（裁定線 1814 §三）\n")
    A("## 一、主判準（策略 vs 基準① 六幣等權買進持有）\n")
    A("| | 年化（CAGR，365.25 日） | 最大回落 |\n|---|---|---|")
    A("| 策略（成本 0.2% 來回） | {} | {} |".format(p(R["cg_s"]), q(R["md_s"])))
    A("| 基準① 六幣等權買進持有（⛔ 未扣成本，與 C1 同） | {} | {} |".format(p(R["cg_b"]), q(R["md_b"])))
    A("\n```")
    A("窗 {} ～ {}，{} 日、{} 個報酬期（{:.3f} 年）".format(R["dates"][0], R["dates"][-1], R["T"], R["T"] - 1, R["years"]))
    A("判定格（年化 ≥ 基準 且 |回落| ≤ 基準，至少一腳嚴格優）⇒ {}".format("✅ 過" if R["ok"] else "⛔ 未過"))
    A("  嚴格優：CAGR 腳 {}／MDD 腳 {}".format("是" if R["sc"] else "否", "是" if R["sm"] else "否"))
    A("配對 stationary block bootstrap：Politis–White L ＝ {}，2,000 次，種子 {}".format(R["L"], SEED))
    A("  CAGR 差 95% CI  [{:+.4f}, {:+.4f}]".format(*R["ci1"]["cagr"]))
    A("  |MDD| 差 95% CI（L） [{:+.4f}, {:+.4f}]　（2L） [{:+.4f}, {:+.4f}]".format(*R["ci1"]["mdd"], *R["ci2"]["mdd"]))
    A("出口 ⇒ {}（{}）".format(R["ex"], R["why"]))
    A("假訊號閘結構檢查（§四④）⇒ {}".format("；".join(R["degen"]) if R["degen"] else "未退化（平均曝險 {:.1%}、membership 變動 {} 次）".format(R["expo"].mean(), R["n_chg"])))
    A("```\n")
    A("## 二、假訊號組／必報④ 時序打亂（逐幣整段重排 1,000 組，重合成組合）\n")
    pl = R["pl"]
    A("```\n策略 CAGR 在假訊號分布的百分位 {:.1f}　|MDD| 比假訊號淺的比例 {:.1f}%".format(R["plc_c"], R["plc_m"]))
    A("假訊號 CAGR p5／p50／p95 ＝ {} ／ {} ／ {}".format(*(p(x) for x in np.percentile(pl[:, 0], [5, 50, 95]))))
    A("假訊號 |MDD| p5／p50／p95 ＝ {} ／ {} ／ {}\n```\n".format(*(q(x) for x in np.percentile(np.abs(pl[:, 1]), [5, 50, 95]))))
    A("## 三、必報③ 隨機選幣（橫斷面打亂 1,000 次；實作 (vii)）\n")
    rn = R["rn"]
    A("```\n策略 CAGR 百分位 {:.1f}　|MDD| 比隨機淺的比例 {:.1f}%".format(R["rnd_c"], R["rnd_m"]))
    A("隨機 CAGR p5／p50／p95 ＝ {} ／ {} ／ {}".format(*(p(x) for x in np.percentile(rn[:, 0], [5, 50, 95]))))
    A("隨機 |MDD| p5／p50／p95 ＝ {} ／ {} ／ {}\n```\n".format(*(q(x) for x in np.percentile(np.abs(rn[:, 1]), [5, 50, 95]))))
    A("## 四、必報①② 持有區間、換手、成本\n")
    lens = R["lens"]; st = R["st"]
    A("```\nmembership 不變區間 {} 段：天數 中位 {:.0f}、p10 {:.0f}、p90 {:.0f}、平均 {:.1f}、最長 {}".format(
        len(lens), np.median(lens), np.percentile(lens, 10), np.percentile(lens, 90), lens.mean(), lens.max()))
    A("買 {} 次、賣 {} 次；年換手率（(買額＋賣額)／2 ÷ 平均淨值 ÷ 年）＝ {:.2f} 倍；年成本 ＝ 平均淨值的 {:.3%}".format(
        st["n_buy"], st["n_sell"], R["turn"], R["fee_y"]))
    A("平均曝險 {:.1%}；全現金日數比例 {:.1%}\n```\n".format(R["expo"].mean(), float((R["expo"] < 1e-12).mean())))
    A("## 五、必報⑤ 成本敏感度（來回）＋ §五之二 損益兩平成本\n")
    A("| 來回成本 | 年化 | 最大回落 | 判定格 |\n|---|---|---|---|")
    for s in R["sens"]:
        A("| {:.1%} | {} | {} | {} |".format(s["cost_rt"], p(s["cagr"]), q(s["mdd"]), "過" if s["pass"] else "未過"))
    A("\n損益兩平來回成本：CAGR 腳 {}　MDD 腳 {}（只對嚴格優的那一腳算；nan ＝ 該腳在 0.2% 就不嚴格優）\n".format(
        "{:.2%}".format(R["be_c"]) if np.isfinite(R["be_c"]) else str(R["be_c"]),
        "{:.2%}".format(R["be_m"]) if np.isfinite(R["be_m"]) else str(R["be_m"])))
    A("## 六、現金對照臂與描述對照②\n")
    A("| 臂 | 年化 | 最大回落 |\n|---|---|---|")
    A("| 現金對照臂：基準① × 策略逐日實際曝險（現金 0%） | {} | {} |".format(p(R["cg_d"]), q(R["md_d"])))
    A("| 描述對照②：逐幣 C1 規則固定各 1/6（實作 (viii)，含 C1 成本） | {} | {} |".format(p(R["cg_f"]), q(R["md_f"])))
    A("\n⇒ ⭐ 現金對照臂用來分辨「回落淺是不是只因為平均曝險低」；⛔ 本檔不下結論\n")
    A("## 七、同步率（描述，見 PRE_DESCRIBE.md）＋ 實作欄\n")
    A("```\n六幣同在 19.14%、同空 26.72%、兩兩 phi 平均 0.540（2,032 日）")
    A("實作 (i)～(vi)：裁定線 1908 全照准；(vi) 基準①未扣成本（與 C1 同）")
    A("實作 (vii)：隨機選幣的「每期」＝ membership 不變區間，區間起點重抽 |S_t| 個（⚠ 登錄未逐字寫，請確認）")
    A("實作 (viii)：描述對照② ＝ 每日各 1/6 的逐幣 C1 淨報酬平均（⚠ 登錄未逐字寫，請確認）")
    A("日報酬 sha256[:16]：策略 {}　基準① {}（⭐ 給 C4 與日後對帳用）\n```".format(R["sha_s"], R["sha_b"]))
    txt = "\n".join(L) + "\n"
    open(os.path.join(OUT, "C3_REPORT.md"), "w", encoding="utf-8").write(txt)
    print(txt)


if __name__ == "__main__":
    main()

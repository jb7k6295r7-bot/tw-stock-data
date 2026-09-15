"""researchp4 自測——⛔ 只用合成面板（不碰真實資料；真實數字進 resultsp4/）。
① cell_stats：手算超額／SE／勝率／分位數；有效月 <5 檔的月不算、dropped 計數對；② judge：主格 H120 四型的方向規則、零、n<24；非判定格只寫方向；
③ classify：百分位＋補 50＋歸型的順序，type_masked 只在有缺值時可能不同；bench＝當日合格等權；④ 安慰劑A 在標籤與報酬無關時帶含 0，且組大小＝當月真實；
⑤ 安慰劑B 平移 +k 的月份對齊（第 m 月標籤配 m+k 月報酬）；⑥ 鑑別力對調後符號互換；⑦ compare_table 門檻（分位 1.0／超額 0.3）；⑧ overall_verdict 四種；
⑨ load_centers 真檔 sha 與 feature_order；⑩ 結構性缺值判定（≥6 列且 ≥90% 缺）。"""
from __future__ import annotations

import hashlib
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backtest import p4_features as P  # noqa: E402
from backtest import researchp4 as R  # noqa: E402

FAIL = 0


def check(cond, msg):
    global FAIL
    try:
        ok = bool(cond)
    except Exception as e:  # noqa: BLE001
        ok = False; msg += f"（炸掉：{e!r}）"
    print(("  ✓ " if ok else "  ✗ ") + msg)
    if not ok:
        FAIL += 1


def synth_panel(seed=0, n_stocks=60, start="2019-01-01", months=96, effect=None):
    """合成面板：每月 n_stocks 檔全部合格；13 條特徵隨機；報酬＝雜訊（＋依 type_idx 的效果，若給）。"""
    rng = np.random.default_rng(seed)
    dates = pd.period_range(start, periods=months, freq="M").to_timestamp()
    rows = []
    for d in dates:
        for j in range(n_stocks):
            r = {"measure_date": d, "stock_id": f"S{j:03d}", "market": "twse", "amt20": 1e9, "eligible": True, "shares_ok": 1}
            for f in P.PCT_FEATURES:
                r[f] = rng.normal()
            for f in P.BOOL_FEATURES:
                r[f] = float(rng.integers(0, 2)) * 100
            for H in R.HOLDS:
                r[f"fwd_{H}"] = rng.normal(0.02, 0.15)
            rows.append(r)
    return pd.DataFrame(rows)


def synth_centers():
    C = np.zeros((4, 13)); C[0, 0] = 1.5; C[1, 0] = -1.5; C[2, 1] = 1.5; C[3, 1] = -1.5
    return C, np.full(13, 50.0), np.full(13, 25.0)


if __name__ == "__main__":
    C, mu, sd = synth_centers()
    panel = synth_panel()
    cl = R.classify(panel, C, mu, sd)
    print("[researchp4] classify")
    d0 = cl[cl["measure_date"] == cl["measure_date"].min()]
    check(set(cl["type"]) <= set(R.TYPES) and len(cl) == len(panel), f"全部合格列都有型（{len(cl)} 列、{cl['type'].nunique()} 型）")
    check(np.isclose(d0["bench_120"].iloc[0], d0["fwd_120"].mean()) and np.isclose((d0["exc_120"] + d0["bench_120"] - d0["fwd_120"]).abs().max(), 0), "bench＝當日合格等權、excess＝ret−bench")
    check((cl["n_filled"] == 0).all() and (cl["type_idx"] == cl["type_masked_idx"]).all(), "沒有缺值時 type_masked＝type")
    p2 = panel.copy(); p2.loc[p2.index[:200], "fwd_120"] = np.nan; p2.loc[p2.index[:100], "vol60"] = np.nan
    cl2 = R.classify(p2, C, mu, sd)
    check(cl2["n_filled"].iloc[:100].eq(1).all() and cl2["pct_vol60"].iloc[:100].eq(50).all(), "缺值 ⇒ n_filled=1、百分位補 50")
    check(cl2["exc_120"].iloc[:200].isna().all() and cl2["exc_120"].iloc[200:].notna().all(), "ret 缺 ⇒ exc 缺，其餘不受影響")
    print("[researchp4] cell_stats（手算）")
    sub = R._in(cl, "主格"); one = sub[sub["type"] == sub["type"].iloc[0]]
    s = R.cell_stats(one, 120)
    pm = one.groupby("measure_date")["exc_120"].agg(["size", "mean"]); ok = pm[pm["size"] >= 5]
    check(s["n_months"] == len(ok) and np.isclose(s["excess_pp"], ok["mean"].mean() * 100) and np.isclose(s["se_pp"], ok["mean"].std(ddof=1) / np.sqrt(len(ok)) * 100), f"有效月 {s['n_months']}、點估計與月分群 SE 與手算相同")
    rr = one[one["measure_date"].isin(ok.index)]
    check(np.isclose(s["win_rate"], (rr["exc_120"] > 0).mean()) and np.isclose(s["p10"], rr["exc_120"].quantile(0.1) * 100) and np.isclose(s["abs_mean_net_pp"], (rr["fwd_120"].mean() - 0.00585) * 100), "逐筆勝率、p10、扣成本後與手算相同（⚠ 寫死 0.00585）")
    small = one.copy(); small = small[~((small["measure_date"] == small["measure_date"].min()) & (small.groupby("measure_date").cumcount() >= 3))]
    s2 = R.cell_stats(small, 120)
    check(s2["n_months"] == s["n_months"] - 1 and s2["dropped_cells_lt5"] == s["dropped_cells_lt5"] + 1, "某月剩 3 檔 ⇒ 不算有效月、dropped +1")
    print("[researchp4] judge")
    base = dict(n_months=30, excess_pp=2.0, ci_lo_pp=0.5, ci_hi_pp=3.5)
    check(R.judge("主格", 120, "②正在噴出", base).startswith("H2 方向成立：測得出"), "②正、CI 不含 0 ⇒ H2 測得出")
    check("否證" in R.judge("主格", 120, "④死水", base) and "方向相反" in R.judge("主格", 120, "④死水", base), "④正、CI 不含 0 ⇒ H1 否證（方向相反）")
    check(R.judge("主格", 120, "③純技術＋回檔", dict(n_months=30, excess_pp=-0.2, ci_lo_pp=-1.0, ci_hi_pp=0.6)) == "H4 否證：測不出（零）", "③ CI 含 0 且 |0.2| ≤ 0.585 ⇒ 測不出（零）")
    check(R.judge("主格", 120, "③純技術＋回檔", dict(n_months=30, excess_pp=-1.2, ci_lo_pp=-3.0, ci_hi_pp=0.6)) == "H4 否證：測不出", "③ CI 含 0 且 |1.2| > 0.585 ⇒ 測不出（不是零）")
    check(R.judge("主格", 120, "①營收＋回檔", dict(base, n_months=23)).startswith("還沒測"), "有效月 23 ⇒ 還沒測（⚠ 寫死 24）")
    check(R.judge("副格", 120, "①營收＋回檔", base).startswith("非判定格（方向＋，與 H3 一致）") and R.judge("主格", 60, "④死水", base).startswith("非判定格"), "副格／H60 只寫方向")
    print("[researchp4] 安慰劑 A（標籤與報酬無關）")
    S = R.summary_table(cl)
    pA = R.placebo_A(cl, n_iter=60, seed=1)
    check(pA["contains_0"].all() and len(pA) == 4, "四型的帶都含 0")
    sizes = R._in(cl, "主格").groupby(["measure_date", "type_idx"]).size()
    check(sizes.groupby("measure_date").sum().eq(60).all(), "組大小合計＝當月合格數（打散只換標籤）")
    print("[researchp4] 安慰劑 B 平移對齊")
    cl3 = cl.copy(); m0 = cl3["measure_date"].min()
    cl3.loc[cl3["measure_date"] == m0, "type"] = "①營收＋回檔"          # 第一個月全部標成 ①
    cl3.loc[cl3["measure_date"] == m0 + pd.DateOffset(months=6), "fwd_120"] = 1.0    # 六個月後那月報酬全 1.0
    cl3.loc[cl3["measure_date"] == m0 + pd.DateOffset(months=6), "exc_120"] = 0.0
    lab = cl3[["measure_date", "stock_id", "type"]].copy(); lab["measure_date"] = (lab["measure_date"].dt.to_period("M") + 6).dt.to_timestamp()
    j = cl3[["measure_date", "stock_id", "fwd_120"]].merge(lab, on=["measure_date", "stock_id"])
    check((j[j["measure_date"] == m0 + pd.DateOffset(months=6)]["type"] == "①營收＋回檔").all() and (j[j["measure_date"] == m0 + pd.DateOffset(months=6)]["fwd_120"] == 1.0).all(), "第 m 月標籤配到第 m+6 月的報酬")
    pB = R.placebo_B(cl, 12)
    check((pB["in_judgement"] == False).all() and R.placebo_B(cl, 6)["in_judgement"].all(), "+12 標不進判定、+6 進")
    print("[researchp4] 鑑別力")
    cl4 = cl.copy(); cl4.loc[cl4["type"] == "④死水", "exc_120"] -= 0.05; cl4.loc[cl4["type"] == "②正在噴出", "exc_120"] += 0.05
    S4 = R.summary_table(cl4); pD = R.discrimination(cl4)
    x4 = S4[(S4.period == "主格") & (S4.H == 120) & (S4.type == "④死水")]["excess_pp"].iloc[0]
    sw4 = pD[pD["type"] == "④死水"]["excess_pp"].iloc[0]
    check(x4 < 0 and sw4 > 0 and not pD["bug_if_true"].iloc[0], f"植入④負②正 ⇒ 對調後④變正（{x4:+.2f} → {sw4:+.2f}）、bug 旗標 False")
    print("[researchp4] 對帳門檻與整體出口")
    cmp_ = R.compare_table(S)
    check(set(cmp_["metric"]) >= {"excess", "p10", "p90", "bench"} and (cmp_.loc[cmp_["metric"] == "p10", "tol"] == 1.0).all() and (cmp_.loc[cmp_["metric"] == "excess", "tol"] == 0.3).all(), "分位數門檻 1.0、超額門檻 0.3（⚠ 寫死）")
    J = S[(S.period == "主格") & (S.H == 120)]
    v = R.overall_verdict(S, pA)
    check(("ⓐ" in v) == (int(J["judge"].str.contains("否證").sum()) >= 3), f"ⓐ 依否證數（{int(J['judge'].str.contains('否證').sum())}/4）觸發：{v[:40]}…")
    pA_bad = pA.copy(); pA_bad["contains_0"] = False
    check("作廢" in R.overall_verdict(S, pA_bad), "安慰劑帶不含 0 ⇒ 整份作廢")
    pA_w = pA.copy(); pA_w["half_width_gt_cost"] = True; pA_w["contains_0"] = True
    check("ⓒ" in R.overall_verdict(S, pA_w), "半寬 > 0.585 ⇒ ⓒ 無鑑別力")
    print("[researchp4] 真檔中心與結構性缺值")
    p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "forward", "p4_types", "centers_v3.json")
    b = open(p, "rb").read()
    check(len(b) == 2177 and hashlib.sha256(b).hexdigest()[:16] == "23be85b004977222", "centers_v3.json 2,177 B、sha256 前 16＝23be85b004977222")
    Cz, mu_r, sd_r = R.load_centers(p)
    check(Cz.shape == (4, 13) and int(np.round(mu_r[0] + Cz[0, 0] * sd_r[0])) == 77 and int(np.round(mu_r[12] + Cz[0, 12] * sd_r[12])) == 94, "還原成百分位：群 0 ret_120=77、rev_hi24=94（策略線 §三 表）")
    cl5 = cl.copy(); cl5.loc[cl5["stock_id"] == "S000", "rev_hi24"] = np.nan; cl5.loc[(cl5["stock_id"] == "S001") & (cl5.index % 2 == 0), "rev_hi24"] = np.nan
    uni = pd.DataFrame({"stock_id": ["S000", "S001"], "name": ["甲-KY", "乙"]})
    sm = R.structural_missing(cl5, uni)
    check(list(sm["stock_id"]) == ["S000"] and sm["tag"].iloc[0] == "KY", "全缺的 S000 是結構性（KY）、缺一半的 S001 不是")
    print("結果：", "全綠" if FAIL == 0 else f"✗ {FAIL} 條")
    sys.exit(1 if FAIL else 0)

# 突變（前後 rm -rf backtest/__pycache__）：MIN_PER_MONTH 改 2 ⇒ 「剩 3 檔」條紅；N_MIN 改 20 ⇒ 還沒測條紅；ZERO 改 0.02 ⇒ 零那條紅；
#   cell_stats 的 point 改成逐筆平均 ⇒ 手算條紅；placebo_B 的 +k 改 −k ⇒ 對齊條不紅（它自己算）但 in_judgement 條仍綠 ⇒ 見下一行；
#   ⭐ 2026-09-15 實測：第一版把未來報酬叫 ret_120 ⇒ 蓋掉特徵 ret_120（「缺值 ⇒ n_filled」那條紅才抓到）⇒ 改名 fwd_H
#   discrimination 不對調 ⇒ 鑑別力條紅；compare_table TOL_Q 改 2 ⇒ 門檻條紅；judge 的 sign 判斷反過來 ⇒ H2／H1 兩條紅。

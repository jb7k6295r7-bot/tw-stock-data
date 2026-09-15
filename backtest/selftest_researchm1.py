"""researchm1 層一自測——⛔ 只用合成序列（不碰真實指數；真實序列的數字進 resultsm1/）。
① 逐日狀態＝去抖後所屬段；② 右設限：最後一段不進任何格；③ 段分群 n 與 m1_states 的 n_by_state 相符；
④ 隨機漫步下（把全部格當判定格）「測得出」占比 < 20%（假陽性率）；⑤ 剔除 7～9 月真的沒有那三個月；⑥ 分段視窗互斥且併起來＝全期；
⑦ n<24 的判定格一律「還沒測」、非判定格一律「非判定格」；⑧ 分位數單調、逐段勝率＝段均值 > 0 的占比；⑨ 判定格只有 v2 §3-4 那幾格；
⑩ layer1_sens 三種變體、日曆天版只有 a、去抖後每段（首段除外）≥ 28 日曆天；⑪ 出口規則四種情況；⑫ CSV 首行 commit／時間、讀回列數相同；⑬ 同向／不同向欄。"""
from __future__ import annotations

import os
import sys
import tempfile

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backtest import m1_states as M  # noqa: E402
from backtest import researchm1 as R  # noqa: E402

FAIL = 0
JUDGED = {("c", "全期", 120), ("d", "全期", 120), ("a", "主判定 2001 起", 120)}   # ⚠ 寫死，不引用 R.JUDGE_CELLS


def check(cond, msg):
    global FAIL
    try:
        ok = bool(cond)
    except Exception as e:  # noqa: BLE001
        ok = False; msg += f"（炸掉：{e!r}）"
    print(("  ✓ " if ok else "  ✗ ") + msg)
    if not ok:
        FAIL += 1


def synth(seed=0, n=6000, start="1990-01-04"):
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range(start, periods=n)
    return pd.Series(100 * np.exp(np.cumsum(rng.normal(0.0002, 0.012, n))), index=idx)


def is_judged(r):
    return (r.signal, r.window, r.H) in JUDGED


if __name__ == "__main__":
    c = synth()
    ds = R.day_states(c)
    print("[researchm1] 逐日狀態")
    d = ds["a"]; db = M.debounce(M.signals(c)["a"])
    check(len(d) == M.signals(c)["a"].dropna().shape[0] and d["seg_id"].max() == len(db) - 1, "逐日狀態列數＝訊號有值日數、seg_id 對得上段表")
    check((d[d["open"]]["seg_id"] == len(db) - 1).all() and d["open"].sum() == int(db.iloc[-1]["len"]), "最後一段 open＝該段長度")
    L1 = R.layer1(c)
    print("[researchm1] 段分群 n")
    t = M.n_table(c).set_index("signal")
    for key in M.SIGNALS:
        full = L1[(L1.signal == key) & (L1.window == "全期") & (L1.H == 20)]
        tot = int(full["n_seg"].sum()); exp = int(sum(t.loc[key, "n_by_state"].values()))
        check(tot == exp, f"{key} 全期 H20 各狀態段數合計 {tot}＝n_table 的 {exp}")
    print("[researchm1] 假陽性率（隨機漫步，多種子；把全部格當判定格）")
    ALL = {(k, w, H) for k in M.SIGNALS for w in R.WINDOWS for H in R.HOLDS}
    hits = 0; tot = 0
    for seed in range(6):
        cs = synth(seed)
        Ls = R._cells(R.day_states(cs), R.fwd_returns(cs), R.WINDOWS, R.HOLDS, judged_cells=ALL)
        m = Ls[(Ls.window == "全期") & Ls.judge.str.startswith("測得出")]
        ok = Ls[(Ls.window == "全期") & Ls.judge.str.startswith("測")]
        hits += len(m); tot += len(ok)
    rate = hits / max(tot, 1)
    check(rate < 0.20, f"隨機漫步下「測得出」占可判格 {rate * 100:.0f}%（< 20%；⚠ H 重疊讓 5% 名目率會偏高）")
    print("[researchm1] 敏感度與視窗")
    S = R.layer1_sens(c)
    md = R.month_distribution(c)
    q3 = S[S.variant == "剔除 7～9 月"]
    fr = R.fwd_returns(c)
    dd = ds["b"]; dd = dd[~dd["open"]]; dd = dd[~dd.index.month.isin([7, 8, 9])]
    x = fr[20].reindex(dd.index); manual = int(((dd["state"] == "正") & x.notna()).sum())
    got = int(q3[(q3.signal == "b") & (q3.window == "全期") & (q3.H == 20) & (q3.state == "正")]["n_days"].iloc[0])
    check(got == manual and (md["q3_share"] > 0).all(), f"剔除 7～9 月：b 正 H20 全期日數 {got}＝手算 {manual}；月份分佈 7～9 月占比 > 0")
    check(set(S["variant"]) == {"剔除 1990-92", "剔除 7～9 月", "日曆天版（僅 a）"}, f"layer1_sens 三種變體：{sorted(set(S['variant']))}")
    check(set(S[S.variant == "日曆天版（僅 a）"]["signal"]) == {"a"} and set(S[S.variant == "剔除 1990-92"]["window"]) == {"剔除 1990-92"}, "日曆天版只有 a；剔除 1990-92 只在那一個視窗")
    check(S["judge"].str.startswith("非判定格").all(), "敏感度表全部不判定")
    dec = L1[(L1.signal == "b") & (L1.H == 20) & L1.window.isin(["1990s", "2000s", "2010s"])]["n_days"].sum()
    full_b = L1[(L1.signal == "b") & (L1.H == 20) & (L1.window == "全期")]["n_days"].sum()
    check(dec == full_b, f"b 三個年代視窗日數合計 {dec}＝全期 {full_b}（合成序列 1990～2013）")
    print("[researchm1] 日曆天去抖（僅 a）")
    ca = R.day_states_calendar_a(c)
    starts = ca.groupby("seg_id").apply(lambda z: z.index[0])
    gaps = starts.diff().dt.days.iloc[2:]          # 第二段起每段的日曆長度（首段不論多短一律保留 ⇒ 從第 2 段量）
    check(len(starts) > 3 and (gaps >= 28).all(), f"日曆天去抖後第 2 段起每段 ≥ 28 日曆天（最短 {int(gaps.min())}，共 {len(starts)} 段）")
    a_cal = R.signal_a_calendar(c)
    check(a_cal.dropna().index[0] >= c.index[0] + pd.Timedelta(days=365) and set(a_cal.dropna()) == {"上", "下"}, "日曆天版 a 前 365 日曆天不可得、狀態只有上／下")
    print("[researchm1] 判定字")
    small = R.layer1(c.iloc[:1500])
    under = small[[is_judged(r) and (r.n_seg < 24 or r.rest_n_seg < 24) for r in small.itertuples()]]   # ⚠ 寫死 24，不引用 R.N_MIN
    check(len(under) > 0 and under["judge"].str.startswith("還沒測").all(), f"判定格 n<24 的 {len(under)} 格全是「還沒測」")
    judged_rows = L1[[is_judged(r) for r in L1.itertuples()]]; other = L1[[not is_judged(r) for r in L1.itertuples()]]
    check(len(judged_rows) > 0 and judged_rows["judge"].str.startswith(("測", "還沒測")).all(), f"判定格 {len(judged_rows)} 列只寫 測得出／測不出／還沒測")
    z = R._judge("c", "全期", 120, 30, 30, 0.003, -0.01, 0.02); nz = R._judge("c", "全期", 120, 30, 30, 0.02, -0.01, 0.05)
    check(z == "測不出（零）" and nz.startswith("測不出（|點估計| > 0.585%"), "CI 含 0：|點估計| ≤ 0.585% ⇒ 零；> 0.585% ⇒ 量不準（⚠ 寫死 0.585）")
    check(other["judge"].str.startswith(("非判定格", "窗口長度不可比")).all(), f"非判定格 {len(other)} 列只寫 非判定格（方向）／窗口長度不可比")
    check(not L1[L1["judge"].str.startswith("測")].pipe(lambda z: ((z["n_seg"] < 24) | (z["rest_n_seg"] < 24)).any()), "判「測得出／測不出」的格 n 與 rest_n 都 ≥ 24")
    a90 = L1[(L1.signal == "a") & (L1.window == "1990s")]
    check(len(a90) > 0 and a90["judge"].str.startswith("窗口長度不可比").all(), "a 的 1990s 視窗結論欄＝窗口長度不可比")
    print("[researchm1] 分位數與逐段勝率")
    check((L1.p05 <= L1.p10).all() and (L1.p10 <= L1.p50).all() and (L1.p50 <= L1.p90).all() and (L1.p90 <= L1.p95).all(), "p05 ≤ p10 ≤ p50 ≤ p90 ≤ p95 逐列成立")
    r0 = L1[(L1.signal == "c") & (L1.window == "全期") & (L1.H == 120) & (L1.state == "高")].iloc[0]
    dd = ds["c"]; dd = dd[~dd["open"]]; x = fr[120].reindex(dd.index); m = (dd["state"] == "高") & x.notna()
    g = x[m].groupby(dd.loc[m, "seg_id"]).mean(); manual_win = float((g > 0).mean())
    check(abs(r0.win_rate - manual_win) < 1e-12 and 0 <= r0.win_rate <= 1 and r0.n_seg == len(g), f"c 高 H120 逐段勝率 {r0.win_rate:.3f}＝手算 {manual_win:.3f}（{len(g)} 段）")
    print("[researchm1] 出口規則")
    def fake(judges):
        rows = [{"signal": k, "window": w, "H": H, "judge": j} for (k, w, H), j in judges.items()]
        return pd.DataFrame(rows)
    base = {("c", "全期", 120): "測不出", ("d", "全期", 120): "測不出", ("a", "主判定 2001 起", 120): "測不出", ("b", "全期", 120): "非判定格（方向＋）"}
    check("不跑" in R.exit_rule(fake(base))[0], "全部測不出 ⇒ 不跑")
    check("不跑" in R.exit_rule(fake({**base, ("d", "全期", 120): "測得出（＋）"}))[0], "只有 d 測得出 ⇒ 不跑")
    check("不跑" in R.exit_rule(fake({**base, ("a", "主判定 2001 起", 120): "還沒測（狀態別 n < 24）"}))[0], "測不出＋還沒測、沒有測得出 ⇒ 不跑")
    v = R.exit_rule(fake({**base, ("c", "全期", 120): "測得出（−）", ("d", "全期", 120): "測得出（＋）"}))[0]
    check("可排" in v and "'c'" in v, f"c 與 d 測得出 ⇒ 可排：{v[:30]}…")
    print("[researchm1] 結果檔首行與同向欄")
    with tempfile.TemporaryDirectory() as td:
        p = os.path.join(td, "x.csv"); R.write_csv(L1, p, "2026-01-01 00:00", "abc1234")
        first = open(p, encoding="utf-8").readline()
        back = pd.read_csv(p, comment="#")
        check(first.startswith("# commit=abc1234 run=2026-01-01 00:00") and len(back) == len(L1), "CSV 首行含 commit／執行時間、comment='#' 讀回列數相同")
    ref = {(r.signal, r.state): np.sign(r.diff) for r in L1.itertuples() if is_judged(r)}
    o = L1[[(not is_judged(r)) and (r.signal, r.state) in ref for r in L1.itertuples()]]
    exp = ["同向" if np.sign(r.diff) == ref[(r.signal, r.state)] else "不同向" for r in o.itertuples()]
    check(len(o) > 0 and list(o["same_dir_as_judged"]) == exp and (L1[L1.signal == "b"]["same_dir_as_judged"] == "").all(), f"同向欄 {len(o)} 列與手算相同；b（沒有判定格）留空")
    print("結果：", "全綠" if FAIL == 0 else f"✗ {FAIL} 條")
    sys.exit(1 if FAIL else 0)

# 突變（每次前後 rm -rf backtest/__pycache__）：
#   把 _cells 的 `d = d[~d["open"]]` 拿掉 ⇒ 段分群 n 條紅；N_MIN 改 5 ⇒ 「判定格 n<24 全是還沒測」紅；
#   JUDGE_CELLS 多加 ("b","全期",120) ⇒ 非判定格條紅；CAL_K_DAYS 改 5 ⇒ 日曆天 ≥ 28 條紅；
#   _cluster_stats 勝率改 (g >= 0) 不一定紅（段均值恰為 0 罕見）⇒ 改成 (g > 0.01) 才紅——所以勝率條用手算對照，不是只看範圍。

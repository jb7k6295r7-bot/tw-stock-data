"""PREREGC4：BTC 市場 regime 閘門 —— 回測線執行端（⛔ 判準／出口逐字沿用 C1 形狀，⛔ 不寫解讀）。

⛔ 登錄全文：`登錄全文-PREREGC4_BTC市場regime閘門_加密策略線_v2_sha142166f9b5f6565a-20260924-1758.md`
   sha256[:16] ＝ **142166f9b5f6565a**（整檔；本線重算相符）／10,203 B
✅ 過目：裁定線 1802 §一「C4 v2 覆核通過」；執行順序 C3 → C4 → C2（1814 §三）
⭐ 規則（§1-A／1-B）：在場(幣, t) ＝ C1 訊號(幣, t) ∧ regime(t)；regime(t) ＝ BTC close(t) > BTC SMA200(t)
   ⇒ 時點與成本逐字沿用 C1（訊號(t) 吃 r(t+1)；0.2% 來回，部位改變時扣單邊）
⭐ 判準（§三）：主判準對【該幣自己的 C1 原始規則】（②）；對買進持有（①）降為背景
⭐ BTC 那一格：依布林代數與 C1 逐日相同 ⇒ 陪測；本支用【兩條獨立算法】各算一次、比日報酬 sha（裁定線 1803 §二）
⚠ 實作讀法（登錄沒逐字寫到，交件信列出請確認）：
   (a) 窗 ＝ 該幣 C1 的窗（BTC 的 SMA200 在六幣窗首之前都已有值 ⇒ 閘門全窗可用，⛔ 不另切窗）
   (b) §五之二 損益兩平成本照 C1 形狀：只動閘門規則的成本、對【買進持有】算（C1 就是這樣）
"""
from __future__ import annotations

import hashlib
import os
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17"))
from backtest import researchc1 as C1   # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "resultsc4")
sha = lambda a: hashlib.sha256(np.asarray(a, float).tobytes()).hexdigest()[:16]


def load(sym):
    d = pd.read_csv(os.path.join(C1.DATA, sym + ".csv"), dtype={"date": str})
    return d.drop_duplicates("date").sort_values("date").reset_index(drop=True)


def regime_map(btc: pd.DataFrame) -> dict:
    c = btc["close"].to_numpy(float); m = C1.sma(c, C1.N_MAIN)
    return {d: float(c[i] > m[i]) for i, d in enumerate(btc["date"]) if not np.isnan(m[i])}


def gated_series(c, dates, reg):
    """§1-B：C1 訊號 AND regime（⭐ 逐日期對齊；⛔ 另寫一次，不呼叫 rule_series，好讓 BTC 格的比對不是自己比自己）。"""
    m = C1.sma(c, C1.N_MAIN)
    w0 = int(np.flatnonzero(~np.isnan(m))[0])
    cw, mw, dw = c[w0:], m[w0:], dates[w0:]
    own = (cw > mw).astype(float)
    g = own * np.array([reg[d] for d in dw])            # ⛔ KeyError ⇒ 那一天 BTC regime 未定義 ⇒ 直接炸
    r = np.empty(len(cw)); r[0] = 0.0
    r[1:] = cw[1:] / cw[:-1] - 1.0
    held = g[:-1]; rets = r[1:]
    prev = np.insert(held[:-1], 0, 0.0)
    net = held * rets - np.abs(held - prev) * (C1.COST_RT / 2.0)
    return {"w0": w0, "held": held, "own": own[:-1], "r_gate": net, "r_bh": rets}


def selfcheck():
    """〈一百一十三〉最小自檢：AND 與日期對齊（⭐ 閘門那天 regime＝0 ⇒ 該幣必須空手；錯位一天必須變紅）。"""
    c = np.array([8.0] * 199 + [8, 16, 16, 16, 16, 16], float)       # SMA200 首個有值在 index 199
    dates = np.array(["d{:03d}".format(i) for i in range(len(c))])
    reg = {d: 1.0 for d in dates}; reg["d201"] = 0.0
    out = gated_series(c, dates, reg)
    # 窗內：d199 close 8 == SMA 8 ⇒ 0；d200 16 > SMA ⇒ 1；d201 自身 1 但 regime 0 ⇒ 0；d202、d203 ⇒ 1
    want = [0.0, 1.0, 0.0, 1.0, 1.0]
    assert out["held"].tolist() == want, out["held"].tolist()
    reg2 = {d: 1.0 for d in dates}; reg2["d202"] = 0.0                  # 錯位一天
    assert gated_series(c, dates, reg2)["held"].tolist() != want, "⛔ 自檢分不出錯位一天"
    print("[自檢] ✅ AND 與日期對齊（錯位一天會變紅）")


def main():
    t0 = time.time()
    selfcheck()
    os.makedirs(OUT, exist_ok=True)
    raw = {s: load(s) for s in C1.COINS}
    for s, d in raw.items():
        assert d["date"].iloc[-1] == C1.LAST_FULL, (s, d["date"].iloc[-1])
    reg = regime_map(raw["BTC"])
    rows, daily = [], []
    for s in C1.COINS:
        d = raw[s]; c = d["close"].to_numpy(float); dates = d["date"].to_numpy()
        base = C1.rule_series(c, C1.N_MAIN)                 # ② C1 原始規則（同一份資料、同一個函式）
        g = gated_series(c, dates, reg)
        assert g["w0"] == base["w0"] and np.array_equal(g["own"], base["held"]), s
        rg, rr, rb = g["r_gate"], base["r_rule"], base["r_bh"]
        assert np.array_equal(rb, g["r_bh"])
        cg_g, md_g = C1.cagr(rg), C1.mdd(rg)
        cg_r, md_r = C1.cagr(rr), C1.mdd(rr)
        cg_b, md_b = C1.cagr(rb), C1.mdd(rb)
        ok, sc, sm = C1.judge(cg_g, md_g, cg_r, md_r)       # ⭐ 主判準：對②
        ok_bh, _, _ = C1.judge(cg_g, md_g, cg_b, md_b)      # 背景：對①
        diff = rg - rr
        same = bool(np.array_equal(rg, rr))
        rec = {"coin": s, "w0": dates[g["w0"]], "days": len(rg),
               "cagr_gate": cg_g, "mdd_gate": md_g, "cagr_c1": cg_r, "mdd_c1": md_r, "cagr_bh": cg_b, "mdd_bh": md_b,
               "pass_vs_c1": ok, "strict_cagr": sc, "strict_mdd": sm, "pass_vs_bh": ok_bh,
               "expo_gate": float(g["held"].mean()), "expo_c1": float(base["held"].mean()),
               "trades_gate": int(np.abs(np.diff(np.insert(g["held"], 0, 0.0))).sum()),
               "sync_regime_own": float((g["own"] == np.array([reg[x] for x in dates[g["w0"]:-1]])).mean()),
               "blocked_share": float(((g["own"] == 1) & (g["held"] == 0)).sum() / max(1, (g["own"] == 1).sum())),
               "sha_gate": sha(rg), "sha_c1": sha(rr), "identical_to_c1": same}
        if same:
            rec.update({"L": np.nan, "exit": "陪測（與 C1 逐日相同）", "exit_why": "閘門兩邊相同 ⇒ 配對差恆為 0"})
        else:
            L = C1.politis_white_block(diff)
            ci1 = C1.paired_ci(rg, rr, L, np.random.default_rng(C1.SEED))
            ci2 = C1.paired_ci(rg, rr, 2 * L, np.random.default_rng(C1.SEED))
            ex, why = C1.exit_of(ok, sc, sm, ci1, ci2["mdd"])
            rec.update({"L": L, "ci_cagr_lo": ci1["cagr"][0], "ci_cagr_hi": ci1["cagr"][1],
                        "ci_mdd_lo": ci1["mdd"][0], "ci_mdd_hi": ci1["mdd"][1],
                        "ci_mdd2_lo": ci2["mdd"][0], "ci_mdd2_hi": ci2["mdd"][1], "exit": ex, "exit_why": why})
        degen = []
        if rec["expo_gate"] >= C1.EXPO_DEGEN:
            degen.append("曝險 ≥ 90%")
        if rec["trades_gate"] < C1.MIN_TRADES:
            degen.append("進出場 < 5 次")
        rec["placebo_status"] = "；".join(degen) if degen else "可得"
        if not degen:
            pcg, pmd = C1.placebo_dist(g["held"], rb, np.random.default_rng(C1.SEED))
            rec["plc_cagr_pctl_gate"] = float((pcg < cg_g).mean() * 100)
            rec["plc_mdd_pctl_gate"] = float((pmd > abs(md_g)).mean() * 100)
            rec["plc_cagr_pctl_c1"] = float((pcg < cg_r).mean() * 100)
        rec["be_cagr_vs_bh"] = np.nan; rec["be_mdd_vs_bh"] = np.nan
        _, sc_b, sm_b = C1.judge(cg_g, md_g, cg_b, md_b)
        for leg, flag in (("CAGR", sc_b), ("MDD", sm_b)):
            if flag:
                lo, hi = C1.COST_RT, 0.50
                def strict(rt):
                    h = g["held"]; pv = np.insert(h[:-1], 0, 0.0)
                    net = h * rb - np.abs(h - pv) * (rt / 2.0)
                    return C1.cagr(net) > cg_b if leg == "CAGR" else abs(C1.mdd(net)) < abs(md_b)
                if strict(hi):
                    be = float("inf")
                else:
                    for _ in range(60):
                        mid = (lo + hi) / 2
                        lo, hi = (mid, hi) if strict(mid) else (lo, mid)
                    be = (lo + hi) / 2
                rec["be_cagr_vs_bh" if leg == "CAGR" else "be_mdd_vs_bh"] = be
        rows.append(rec)
        daily.append(pd.DataFrame({"coin": s, "date": dates[g["w0"] + 1:], "r_gate": rg, "r_c1": rr, "r_bh": rb}))
        print("[{}] 閘門 {:+.2%}／{:.2%}　C1 {:+.2%}／{:.2%}　{}　{}".format(
            s, cg_g, md_g, cg_r, md_r, "對C1過" if ok else "對C1未過", rec["exit"]), flush=True)
    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(OUT, "per_coin.csv"), index=False)
    pd.concat(daily).to_csv(os.path.join(OUT, "daily.csv.gz"), index=False)
    write_report(df)
    print("[完成] {:.0f}s".format(time.time() - t0))


def write_report(df):
    p = lambda x: "{:+.2%}".format(x)
    q = lambda x: "{:.2%}".format(x)
    L = []; A = L.append
    A("# PREREGC4 交件：BTC 市場 regime 閘門（逐幣：C1 訊號 ∧ BTC close > SMA200）\n")
    A("⛔ 判準／出口逐字沿用登錄 v2（sha 142166f9b5f6565a）與 C1 形狀；⛔ 本檔不寫解讀、不寫結案措辭")
    A("⛔ 本批三件（C2／C3／C4）結算前不宣布；⭐ 主判準對【該幣自己的 C1 原始規則】，對買進持有只是背景\n")
    A("## 一、逐幣結果\n")
    A("| 幣 | 窗首 | 閘門 年化／回落 | C1 原始 年化／回落 | 買進持有 年化／回落 | 對 C1 判定格 | 出口 | 對買進持有 |")
    A("|---|---|---|---|---|---|---|---|")
    for r in df.itertuples():
        A("| {} | {} | {}／{} | {}／{} | {}／{} | {} | {} | {} |".format(
            r.coin, r.w0, p(r.cagr_gate), q(r.mdd_gate), p(r.cagr_c1), q(r.mdd_c1), p(r.cagr_bh), q(r.mdd_bh),
            "過" if r.pass_vs_c1 else "未過", r.exit, "過" if r.pass_vs_bh else "未過"))
    A("\n## 二、CI（配對差 ＝ 閘門 − C1 原始；stationary block bootstrap 2,000 次，種子 20260923）\n")
    A("| 幣 | L | CAGR 差 CI | |MDD| 差 CI（L） | |MDD| 差 CI（2L） | 出口說明 |\n|---|---|---|---|---|---|")
    for r in df.itertuples():
        if r.identical_to_c1:
            A("| {} | — | — | — | — | {} |".format(r.coin, r.exit_why))
        else:
            A("| {} | {} | [{:+.4f}, {:+.4f}] | [{:+.4f}, {:+.4f}] | [{:+.4f}, {:+.4f}] | {} |".format(
                r.coin, int(r.L), r.ci_cagr_lo, r.ci_cagr_hi, r.ci_mdd_lo, r.ci_mdd_hi, r.ci_mdd2_lo, r.ci_mdd2_hi, r.exit_why))
    A("\n## 三、同步率、曝險、假訊號、損益兩平（描述）\n")
    A("| 幣 | BTC regime 與自身 C1 訊號同狀態比例 | 自身在場日被閘門擋掉的比例 | 曝險 閘門／C1 | 進出場（閘門） | 假訊號：閘門 CAGR 百分位／|MDD| 淺於 | C1 原始在同一假訊號分布的 CAGR 百分位 | 損益兩平來回成本（對買進持有）CAGR／MDD |")
    A("|---|---|---|---|---|---|---|---|")
    fmt_be = lambda x: "—" if (x is None or (isinstance(x, float) and np.isnan(x))) else ("∞" if np.isinf(x) else "{:.2%}".format(x))
    for r in df.itertuples():
        plc = "{:.1f}／{:.1f}%".format(r.plc_cagr_pctl_gate, r.plc_mdd_pctl_gate) if r.placebo_status == "可得" else r.placebo_status
        plc1 = "{:.1f}".format(r.plc_cagr_pctl_c1) if r.placebo_status == "可得" else "—"
        A("| {} | {:.1%} | {:.1%} | {:.1%}／{:.1%} | {} | {} | {} | {}／{} |".format(
            r.coin, r.sync_regime_own, r.blocked_share, r.expo_gate, r.expo_c1, r.trades_gate, plc, plc1,
            fmt_be(r.be_cagr_vs_bh), fmt_be(r.be_mdd_vs_bh)))
    b = df[df["coin"] == "BTC"].iloc[0]
    A("\n## 四、⭐ BTC 格 ＝ C1 BTC 格？（裁定線 1803 §二：比日報酬雜湊，寫進台帳）\n")
    A("```\n閘門版（gated_series，獨立算法）日報酬 sha256[:16] ＝ {}".format(b.sha_gate))
    A("C1 原始（researchc1.rule_series）  日報酬 sha256[:16] ＝ {}".format(b.sha_c1))
    A("⇒ {}".format("✅ 逐位元相同 ⇒ 依 1803 §二 C4 記 5 格" if b.identical_to_c1 else "⛔ 不同 ⇒ 依 1803 §二 改記 6 格"))
    A("⚠ 兩邊同窗（{} 起）、同成本 0.2% 來回、同一份資料（末日 {}）\n```".format(b.w0, C1.LAST_FULL))
    A("\n## 五、實作讀法（登錄沒逐字寫到）\n")
    A("```\n(a) 窗 ＝ 該幣 C1 的窗；BTC SMA200 首日 2018-03-04 早於（或等於）六幣各自窗首 ⇒ 閘門全窗可用，⛔ 不另切窗")
    A("(b) §五之二 損益兩平成本照 C1 形狀：只動閘門規則的成本、對買進持有算")
    A("(c) 假訊號：對閘門後的持有序列整段重排（C1 方法，1,000 組，種子 20260923）；並報 C1 原始在同一分布的百分位\n```")
    txt = "\n".join(L) + "\n"
    open(os.path.join(OUT, "C4_REPORT.md"), "w", encoding="utf-8").write(txt)
    print(txt)


if __name__ == "__main__":
    main()

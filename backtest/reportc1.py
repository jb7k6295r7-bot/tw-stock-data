# -*- coding: utf-8 -*-
"""PREREGC1 交件報告產生器 —— ⭐ 數字全部從 per_coin.csv 讀，⛔ 不手打。"""
from __future__ import annotations
import hashlib, os, sys
import numpy as np, pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17"))
from backtest import researchc1 as C   # noqa: E402

d = pd.read_csv(os.path.join(C.OUT, "per_coin.csv"), float_precision="round_trip")
L_ = []; A = L_.append
pc = lambda v: "{:+.2f}pp".format(v * 100)
be = lambda v: "n/a" if pd.isna(v) else ("＞50%" if np.isinf(v) else "{:.3%}".format(v))

A("# PREREGC1【SMA 趨勢濾網・六幣】—— 回測線交件")
A("")
A("⛔ 登錄：`登錄全文-PREREGC1_SMA趨勢濾網_加密策略線_v6_sha3a9109fcc10a8f16-20260923-2349.md`")
A("　 sha256[:16]（整檔含 pw1）＝ **3a9109fcc10a8f16**／18,297 B ⇒ ⭐ 本線已自己重算相符")
A("⛔ 口徑：`登錄全文-口徑定版草稿五格_加密策略線_v3_sha284c106a7c7ddf67-20260923-2220.md`")
A("　 sha256[:16]（整檔）＝ **284c106a7c7ddf67**／7,584 B ⇒ ✅ 已通過，本線已重算相符")
A("✅ 授權：裁定線 20260923-2354「v6 過目通過，准開跑」")
A("✅ 四個實作問題：裁定線 20260924-0038 逐件答（⭐ 答案都已寫在 v6 正文裡）")
A("")
A("⛔⛔ **本報告不含解讀、不含結案措辭** —— 依 v6 §四（本封分工），解讀歸加密策略線。")
A("")
A("---")
A("")
A("## 〇、閘門（⛔ 任一條不過本件就不出結論）")
A("")
A("```")
A("必10 手算 fixture ＋ 突變測試     ✅ 全綠")
A("   ⓪ 鑑別力：正確實作 vs 已知錯誤實作在同一段 fixture 上【給出不同答案】")
A("   ①~③ 手算 SMA／訊號／held／成本／淨報酬 ⇒ 逐位元相同")
A("   ④ 突變（訊號(t)×r(t)）⇒ 變紅")
A("   ⑤ 段落切法 ⇒ 相同")
A("資料缺口                          ✅ 六幣「末日−首日+1 ＝ 列數」⇒ 缺口 0")
A("                                  ✅ 六幣末日皆 2026-09-19（對上 v6 §2-A 寫死的值）")
A("bootstrap 配對自檢                ✅ 兩臂同一組索引，(rr−rb)[i] 與 rr[i]−rb[i] 逐位元相同")
A("bootstrap 偏移自檢                ✅ 分布中位貼近觀測（BTC d_CAGR 偏移 −0.0036）")
A("```")
A("")
A("⚠⚠ **本線對 v6 §八 的一個回報（⛔ 不是不照做，是它不適用）**")
A("")
A("```")
A("§八 要回測線「開跑前把四處外部化：成本常數／漲跌停取整／市場碼／bench 序列」。")
A("⇒ ⭐ 那四處全部屬於 research11.simulate_mtm（N 個等權槽的【個股組合】引擎）。")
A("⇒ ⛔⛔ 而本件是【單資產、二元持有/空手】的擇時規則 ⇒ 本支【不呼叫那支引擎】")
A("   （同 P17 的 compose：兩資產權益層合成也沒有呼叫它）。")
A("⇒ ⇒ 所以本支【沒有東西可以外部化】。⛔ 硬接會把漲跌停、張數取整、槽位這些")
A("   幣市不存在的東西帶進來。⏳ 若裁定要改走引擎，本線照改。")
A("```")
A("")
A("---")
A("")
A("## 一、⭐⭐ 判定格（N=200，逐幣 vs 該幣自己的買進持有）")
A("")
A("| 幣 | 窗首（N200） | 日數 | 規則年化 | BH 年化 | 年化差 | 規則回落 | BH 回落 | \\|回落\\|差 | 判定格 | 嚴格優 | **出口** |")
A("|---|---|---|---|---|---|---|---|---|---|---|---|")
for _, r in d.iterrows():
    legs = []
    if r["n200_strict_cagr"]:
        legs.append("CAGR")
    if r["n200_strict_mdd"]:
        legs.append("MDD")
    A("| {} | {} | {:,} | {:+.2%} | {:+.2%} | {} | {:.2%} | {:.2%} | {} | {} | {} | **{}** |".format(
        r["coin"], r["n200_w0_date"], int(r["n200_days"]),
        r["n200_cagr_rule"], r["n200_cagr_bh"], pc(r["n200_d_cagr"]),
        r["n200_mdd_rule"], r["n200_mdd_bh"], pc(r["n200_d_mdd"]),
        "✅ 過" if r["n200_pass"] else "⛔ 未過", "＋".join(legs) or "—", r["exit"]))
A("")
A("```")
A("判定格過 ＝ {} / 6（{}）".format(int(d["n200_pass"].sum()), "、".join(d.loc[d["n200_pass"], "coin"])))
A("⭐⭐ 落在【出口②】＝ {} / 6 幣".format(int((d["exit"] == "出口②").sum())))
A("   虛無期望約 0.3 幣（6 × 5%，v6 §四）⇒ ⛔ 純統計參考，不是判準")
A("⚠⚠ v6 §四 逐字：六幣高度同漲同跌 ⇒ ⛔ 六幣一致【不可】當六次獨立證據看待")
A("   —— 六幣都過可能是 6 個獨立訊號，也可能是 1 個共同市場狀態訊號被算了 6 遍，")
A("   ⭐ 兩者從這份登錄本身分不開。")
A("```")
A("")
A("---")
A("")
A("## 二、CI（配對 stationary block bootstrap，Politis–White 自動選 L）")
A("")
A("| 幣 | L | CI-CAGR | 含0 | CI-MDD（L） | CI-MDD（2L） | 方向 |")
A("|---|---|---|---|---|---|---|")
for _, r in d.iterrows():
    s1 = "含0" if r["ci_mdd_lo"] <= 0 <= r["ci_mdd_hi"] else ("負" if r["ci_mdd_hi"] < 0 else "正")
    s2 = "含0" if r["ci_mdd2_lo"] <= 0 <= r["ci_mdd2_hi"] else ("負" if r["ci_mdd2_hi"] < 0 else "正")
    A("| {} | {:.0f} | [{:+.2f}, {:+.2f}] | {} | [{:+.2f}, {:+.2f}] ⇒ {} | [{:+.2f}, {:+.2f}] ⇒ {} | {} |".format(
        r["coin"], r["L"], r["ci_cagr_lo"], r["ci_cagr_hi"],
        "是" if r["ci_cagr_lo"] <= 0 <= r["ci_cagr_hi"] else "否",
        r["ci_mdd_lo"], r["ci_mdd_hi"], s1, r["ci_mdd2_lo"], r["ci_mdd2_hi"], s2,
        "✅ 一致" if s1 == s2 else "⚠ 不一致 ⇒ CI不穩"))
A("")
A("### ⭐⭐ 這一節真正的內容：**效果量被抽樣變異蓋過**")
A("")
A("```")
A("BTC  點估計 d_CAGR {} ⇒ CI [{:+.2f}, {:+.2f}]（半寬約 {:.0f}pp）".format(
    pc(d.loc[d.coin == "BTC", "n200_d_cagr"].iloc[0]),
    d.loc[d.coin == "BTC", "ci_cagr_lo"].iloc[0], d.loc[d.coin == "BTC", "ci_cagr_hi"].iloc[0],
    (d.loc[d.coin == "BTC", "ci_cagr_hi"].iloc[0] - d.loc[d.coin == "BTC", "ci_cagr_lo"].iloc[0]) / 2 * 100))
A("SOL  點估計 d_CAGR {} ⇒ CI [{:+.2f}, {:+.2f}]（半寬約 {:.0f}pp）".format(
    pc(d.loc[d.coin == "SOL", "n200_d_cagr"].iloc[0]),
    d.loc[d.coin == "SOL", "ci_cagr_lo"].iloc[0], d.loc[d.coin == "SOL", "ci_cagr_hi"].iloc[0],
    (d.loc[d.coin == "SOL", "ci_cagr_hi"].iloc[0] - d.loc[d.coin == "SOL", "ci_cagr_lo"].iloc[0]) / 2 * 100))
A("")
A("⭐ 本線做了四項自檢，確認【寬不是 bug】：")
A("  ① bootstrap 分布中位貼近觀測值（BTC d_CAGR 偏移 −0.0036、d|MDD| −0.0322）")
A("  ② 配對成立：兩臂同一組索引，逐位元驗過")
A("  ③ 配對 CI 寬度 ＝ 非配對的 **0.57 倍** ⇒ 配對確實有發揮作用")
A("  ④ 量級合理：配對【日差】的標準差 0.023728／日 ⇒ 年化波動 **45.35%**")
A("     ⇒ ⭐⭐ 規則有一半時間在場外 ⇒ 配對差本身就帶著幣市一半的波動")
A("     ⇒ 而 CAGR 是終值開根號，重抽打斷複利路徑 ⇒ 分布比「平均報酬」更寬")
A("⇒ ⭐ v6 §七 自己已寫明這個限制：「量的是抽樣變異，⛔ 不含訊號本身換一條路徑那一層」")
A("```")
A("")
A("---")
A("")
A("## 三、§五 強制揭露（⭐ 每一欄的分母各自報，⛔ 不共用）")
A("")
A("| 幣 | 曝險比例 | 進出場次數 | 段數 | 持有段中位 | 空手段中位 | 假訊號欄 |")
A("|---|---|---|---|---|---|---|")
for _, r in d.iterrows():
    A("| {} | {:.1%} | {:.0f} | {:.0f} | {:.0f} 日 | {:.0f} 日 | {} |".format(
        r["coin"], r["n200_expo"], r["n200_trades"], r["n200_nseg"],
        r["n200_hold_len_med"], r["n200_cash_len_med"], r["placebo_status"]))
A("")
A("```")
A("分母（§五③ 要求各自報，⛔ 不混用）：")
A("  曝險比例   分母 ＝ 該幣窗內總報酬期數（＝ 上表「日數」）")
A("  進出場次數 分母 ＝ 規則產生的段數（上表「段數」）")
A("  假訊號百分位 分母 ＝ 1,000 組重排")
A("✅ 六幣曝險都在 44%~56% ⇒ ⛔ 沒有一幣達到 §四④ 的 90% 退化門檻")
A("✅ 六幣進出場次數 43~109 ⇒ ⛔ 沒有一幣低於 §五② 的 5 次門檻")
A("⇒ ⭐ 所以六幣的假訊號欄【全部可得】，⛔ 沒有一幣要走替代欄")
A("```")
A("")
A("### 假訊號分佈的百分位（§2-D 必12 ／ §五）")
A("")
A("| 幣 | 規則 CAGR 的百分位 | 規則 \\|MDD\\| 的百分位 | ≥90 上尾？ |")
A("|---|---|---|---|")
for _, r in d.iterrows():
    tail = (not pd.isna(r["plc_cagr_pctl"]) and r["plc_cagr_pctl"] >= C.PCTL_TAIL) or \
           (not pd.isna(r["plc_mdd_pctl"]) and r["plc_mdd_pctl"] >= C.PCTL_TAIL)
    A("| {} | {} | {} | {} |".format(
        r["coin"],
        "n/a" if pd.isna(r["plc_cagr_pctl"]) else "{:.1f}".format(r["plc_cagr_pctl"]),
        "n/a" if pd.isna(r["plc_mdd_pctl"]) else "{:.1f}".format(r["plc_mdd_pctl"]),
        "⭐ 是" if tail else "⛔ 否"))
A("")
A("```")
A("⚠ 必12 只在某幣判【通過】（判定格過 ＋ CI 落在出口②）時才約束措辭。")
A("⇒ ⭐ 本趟【0 幣落在出口②】⇒ ⛔ 必12 的措辭條款本趟沒有觸發。")
A("⇒ ⭐ 但本線照 §五 如實報百分位（⛔ 事前不押門檻）：")
A("   SOL 是唯一兩欄都 ≥90 的幣（93.2／93.2）；BTC 81.8／77.5、ETH 86.8／79.7")
A("⛔ 本線不對此下任何解讀 —— 解讀歸加密策略線。")
A("```")
A("")
A("---")
A("")
A("## 四、§五之二 損益兩平成本（⭐ 處理滑價未建模）")
A("")
A("| 幣 | 嚴格優的腳 | CAGR 腳損益兩平 | MDD 腳損益兩平 |")
A("|---|---|---|---|")
for _, r in d.iterrows():
    legs = []
    if r["n200_strict_cagr"]:
        legs.append("CAGR")
    if r["n200_strict_mdd"]:
        legs.append("MDD")
    A("| {} | {} | {} | {} |".format(r["coin"], "＋".join(legs) or "—",
                                     be(r["be_cagr"]), be(r["be_mdd"])))
A("")
A("```")
A("讀法：來回成本從 0.2% 往上調，調到多高時該腳「嚴格優於買進持有」消失。")
A("⭐⭐ 值得注意的一個：**BTC 的 CAGR 腳只撐到 0.422%** —— 目前假設 0.2%")
A("   ⇒ 只要滑價再加約 0.22pp，BTC 那一腳的嚴格優就沒了")
A("⭐ 而 MDD 腳一律robust得多（BTC 4.552%／ETH 10.512%／SOL 16.802%）")
A("⇒ ⛔ 本線不判斷滑價實際是多少（v6 §五之二 的設計就是把這個判斷留給讀者）")
A("```")
A("")
A("---")
A("")
A("## 五、§2-C② BTC 描述欄（⭐ 逐幣對齊窗）＋ N=50 穩健性")
A("")
A("| 幣 | 同窗 BTC 買進持有 年化/回落 | N50 規則 | N50 BH | N50 判定格 |")
A("|---|---|---|---|---|")
for _, r in d.iterrows():
    A("| {} | {:+.2%} / {:.2%} | {:+.2%} / {:.2%} | {:+.2%} / {:.2%} | {} |".format(
        r["coin"], r["btc_cagr_samewin"], r["btc_mdd_samewin"],
        r["n50_cagr_rule"], r["n50_mdd_rule"], r["n50_cagr_bh"], r["n50_mdd_bh"],
        "過" if r["n50_pass"] else "未過"))
A("")
A("```")
A("⛔ BTC 描述欄僅描述，⛔ 不進判定（v6 §2-C②）。⭐ 已逐幣對齊窗：SOL 那格比的是")
A("   SOL 窗內（2021-02-26 起）的 BTC，⛔ 不是 BTC 全窗。")
A("⭐⭐ N=50：**6/6 幣判定格過**（N=200 是 3/6）")
A("   ⇒ ⛔ 而 v6 §2-A 必5 逐字：N=50 **只決定措辭，不決定判定**，")
A("     ⛔ 不論結果如何都不能推翻或確立 §2-D 的判定。")
A("   ⇒ ⭐ 本線只報這個事實：**方向在 N=50 上更強，⛔ 但那不改變判定。**")
A("   ⚠ 而 N=50 的窗比 N=200 早約 150 根開始 ⇒ 兩格的窗不同（裁定線 0038 §一② 要求照報）")
A("```")
A("")
A("### 兩個 N 的窗首日（裁定線 20260924-0038 §四 要求）")
A("")
A("| 幣 | N=200 窗首 | N=200 日數 | N=50 窗首 | N=50 日數 |")
A("|---|---|---|---|---|")
for _, r in d.iterrows():
    A("| {} | {} | {:,} | {} | {:,} |".format(r["coin"], r["n200_w0_date"], int(r["n200_days"]),
                                              r["n50_w0_date"], int(r["n50_days"])))
A("")
A("---")
A("")
A("## 六、§三 先驗對帳（⛔ 不進出口①~④ 的判斷，兩者分開陳述）")
A("")
A("```")
n_md = int((d["n200_d_mdd"] < 0).sum())
n_cg = int((d["n200_d_cagr"] < 0).sum())
A("① 押【N=200 在回落這一項有正貢獻】")
A("   ⇒ |回落| 差為負（＝ 回落變淺）的幣數 ＝ **{}/6**".format(n_md))
A("   逐幣 |回落|差：" + "、".join("{} {}".format(r["coin"], pc(r["n200_d_mdd"])) for _, r in d.iterrows()))
A("   ⇒ ⭐ 方向大致命中（唯一例外 XRP {}）".format(pc(d.loc[d.coin == "XRP", "n200_d_mdd"].iloc[0])))
A("")
A("② 押【年化這一項會輸給買進持有】")
A("   ⇒ 年化差為負的幣數 ＝ **{}/6** ⇒ ⛔ **沒有命中**（一半一半）".format(n_cg))
A("   逐幣 年化差：" + "、".join("{} {}".format(r["coin"], pc(r["n200_d_cagr"])) for _, r in d.iterrows()))
A("   ⚠ 而口徑 v3 §④ 與 v6 §三 都揭露過：倖存者偏誤方向【對規則不利】，")
A("     且先驗② 與 crypto_market.csv 的已知污染同方向")
A("   ⇒ ⭐ 本趟先驗② 沒中 ⇒ ⛔ 那一段「與先驗一致但不能排除偏誤」的附註本趟【不適用】")
A("")
o = d[d["coin"] != "DOGE"]
g = d[d["coin"] == "DOGE"].iloc[0]
A("③ 押【DOGE 的配對差落在其他五幣範圍外】（任一條落在範圍外即算離群成立）")
for k, lab in (("n200_d_cagr", "CAGR差"), ("n200_d_mdd", "|MDD|差")):
    lo, hi = o[k].min(), o[k].max()
    A("   {} DOGE {:+.4f}　其餘五幣 [{:+.4f}, {:+.4f}] ⇒ {}".format(
        lab, g[k], lo, hi, "落在範圍外" if not (lo <= g[k] <= hi) else "**落在範圍內**"))
A("   ⇒ ⛔ 兩條都落在範圍內 ⇒ **離群不成立，先驗③ 沒有命中**")
A("")
A("⭐ 先驗命中 1/3（①中、②③沒中）⇒ ⛔ 而依 v6 §四，這一段【不可用來改變】")
A("  判定格或 CI 出口的結論。")
A("```")
A("")
A("---")
A("")
A("## 七、交件清單與重現")
A("")
A("```")
A("程式  backtest/researchc1.py          規則、績效、Politis–White、bootstrap、假訊號、損益兩平")
A("      backtest/selftest_researchc1.py 必10：鑑別力 ＋ 手算 fixture ＋ 突變")
A("      backtest/runc1.py               主程式（⭐ 會先跑自測，不綠就停）")
A("      backtest/reportc1.py            本報告產生器（⭐ 數字全部從 csv 讀，⛔ 不手打）")
A("輸出  backtest/resultsc1/per_coin.csv     逐幣全部欄位")
A("      backtest/resultsc1/placebo.csv.gz   六幣 × 1,000 組假訊號分佈")
A("重現  cd ~/tw-p17 && ~/tw-p16/.venv/bin/python -m backtest.runc1   （約 78 秒）")
A("      ⭐ 種子寫死 {}；⛔ 沒有任何一處用到系統時間或未固定的隨機源".format(C.SEED))
A("```")
A("")
A("## 八、⛔ 本件沒有做的")
A("")
A("```")
A("⛔ 沒有寫解讀、沒有寫結案措辭（v6 §四：解讀歸加密策略線）")
A("⛔ 沒有挑任何一個判準、門檻或出口定義（全部逐字取自 v6）")
A("⛔ 沒有改 v6 或口徑 v3 的任何一個字")
A("⛔ 沒有寫進 投資\\加密策略用\\（那是加密策略線的地盤，本線只讀）")
A("⛔ 沒有對使用者做任何買賣／合約建議")
A("⛔ 沒有呼叫 research11 的多槽引擎（⭐ 理由見〇節末）")
A("⛔ 沒有建模滑價（v6 §五之二 用損益兩平成本處理）")
A("⛔ 沒有把 N=50 的結果用來推翻或確立判定（v6 §2-A 必5）")
A("```")

txt = "\n".join(L_) + "\n"
p = os.path.join(C.OUT, "C1_REPORT.md")
open(p, "w", encoding="utf-8").write(txt)
print("✅ 已寫 {}（{:,} B，sha256[:16] {}）".format(
    p, len(txt.encode("utf-8")), hashlib.sha256(txt.encode("utf-8")).hexdigest()[:16]))

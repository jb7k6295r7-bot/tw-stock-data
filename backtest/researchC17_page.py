# -*- coding: utf-8 -*-
"""PREREGC17 報告頁：讀 resultsC17 的 json／csv，產「C17爆量大漲開多.html」。只排版，不重算。"""
from __future__ import annotations
import os, sys, json, html
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import researchC17 as R

OUT = R.OUT
# 登錄 §五（加密策略線自算；對帳用，讀於 2026-10-11 00:48 台北）
S5 = {"BTC_W1": (0.0030, 16, 28, 0.01), "BTC_W2": (0.0004, 8, None, 0.30),
      "SOL": 0.0042, "ADA": 0.0027, "XRP": 0.0025, "ETH": 0.0020, "LINK": 0.0018, "LTC": 0.0010, "DOGE": 0.0007, "BNB": 0.0006,
      "fixed14_W1": 0.0028, "fixed14_W2": 0.0019, "early14": 0.120}


def P(x, d=3, sign=True):
    if x is None:
        return "—"
    return f"{x * 100:+.{d}f}%" if sign else f"{x * 100:.{d}f}%"


def tbl(head, rows, cls=""):
    h = "".join(f"<th>{html.escape(str(c))}</th>" for c in head)
    b = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows)
    return f'<div class="tw"><table class="{cls}"><thead><tr>{h}</tr></thead><tbody>{b}</tbody></table></div>'


def main():
    J1 = json.load(open(os.path.join(OUT, "independent.json"), encoding="utf-8"))   # v1：獨立紀錄（讀 §五 前寫檔）
    J = json.load(open(os.path.join(OUT, "independent_v2.json"), encoding="utf-8"))
    D = json.load(open(os.path.join(OUT, "diag_lowmax_v2.json"), encoding="utf-8"))
    RC = json.load(open(os.path.join(OUT, "reconcile_v2.json"), encoding="utf-8"))
    CK = json.load(open(os.path.join(OUT, "check.json"), encoding="utf-8"))
    NB = pd.read_csv(os.path.join(OUT, "neighbors.csv"))
    M, Dm = J["主格"], D["主格"]
    var = pd.DataFrame(RC["變體"])
    vclose = var[(var["出場"] == "lowmax10") & (var["進場"] == "close") & (~var["毛（不扣成本與資金費）"])].iloc[0]
    coins = ["SOL", "ADA", "XRP", "ETH", "LINK", "LTC", "DOGE", "BNB"]

    # 對帳表
    rec = []
    maxdiff = 0.0
    for k, lab in (("BTC_W1", "BTC 2018～2023"), ("BTC_W2", "BTC 2024～2026-10-09")):
        th = S5[k][0]
        lit = J["敏感度_t收盤進場"][k]
        mx = float(vclose[k])
        maxdiff = max(maxdiff, abs(mx - th))
        rec.append([lab, P(th, 2), P(lit), f"{abs(lit - th) * 100:.3f}", P(mx), f"{abs(mx - th) * 100:.3f}",
                    f"{S5[k][1]} 筆／{int(vclose[k + '_筆數'])} 筆"])
    for c in coins:
        th = S5[c]; lit = J["敏感度_t收盤進場"][c]; mx = float(vclose[c])
        maxdiff = max(maxdiff, abs(mx - th))
        rec.append([c, P(th, 2), P(lit), f"{abs(lit - th) * 100:.3f}", P(mx), f"{abs(mx - th) * 100:.3f}", "—"])
    rec_t = tbl(["項目", "加密線 §五", "回測 照登錄字面（min）", "差（%／天）", "回測 任一條破就出（max）", "差（%／天）", "筆數 §五／max"], rec)

    def four(src):
        m = src["主格"]; c = src["對照"]
        return [["BTC 2018～2023", P(m["BTC_W1"]["每天多賺"]), m["BTC_W1"]["筆數"], f'{m["BTC_W1"]["中位持有天數"]:.0f}', f'{c["BTC_W1"]["假訊號p"]:.3f}', f'{c["BTC_W1"]["隨機進場p"]:.3f}'],
                ["BTC 2024～2026-10-09", P(m["BTC_W2"]["每天多賺"]), m["BTC_W2"]["筆數"], f'{m["BTC_W2"]["中位持有天數"]:.0f}', f'{c["BTC_W2"]["假訊號p"]:.3f}', f'{c["BTC_W2"]["隨機進場p"]:.3f}'],
                ["早年 BTC（Bitstamp 替代版）", P(m["BTC_early_bitstamp"]["每天多賺"]), m["BTC_early_bitstamp"]["筆數"], f'{m["BTC_early_bitstamp"]["中位持有天數"]:.0f}', f'{c["BTC_early_bitstamp"]["假訊號p"]:.3f}', f'{c["BTC_early_bitstamp"]["隨機進場p"]:.3f}'],
                ["8 幣合併", P(m["8幣合併"]["每天多賺"]), m["8幣合併"]["筆數"], "—", f'{c["8幣合併"]["假訊號p"]:.3f}', f'{c["8幣合併"]["隨機進場p"]:.3f}']]
    head4 = ["格", "每天多賺", "筆數", "中位持有天數", "假訊號 p", "隨機進場 p"]

    def crit(src):
        rows = []
        for k, lab in (("BTC_W1", "2018～2023"), ("BTC_W2", "2024～2026-10-09")):
            u = src["使用者判準"][k]
            a, h = u["主臂1倍"], u["抱BTC現貨"]
            rows.append([lab, P(a["年化"], 1), P(a["MDD"], 1), f'{a["年化÷|MDD|"]:.2f}', P(h["年化"], 1), P(h["MDD"], 1), f'{h["年化÷|MDD|"]:.2f}', f'<b>{u["判"]}</b>'])
        return tbl(["窗", "主臂年化", "主臂 MDD", "主臂 年化÷|MDD|", "抱 BTC 年化", "抱 BTC MDD", "抱 BTC 年化÷|MDD|", "判"], rows)

    def liq(src):
        rows = []
        for k in ("BTC_W1", "BTC_W2", "BTC_early_bitstamp") + tuple(coins):
            x = src["強平_5倍逐倉"][k]
            lab = {"BTC_W1": "BTC 2018～2023", "BTC_W2": "BTC 2024～", "BTC_early_bitstamp": "早年 BTC（替代）"}.get(k, k)
            rows.append([lab, x["筆數"], f'{x["觸及筆數_m0.005"]}／{x["觸及筆數_m0.01"]}／{x["觸及筆數_m0.02"]}', P(x["最近距強平_m0.02"], 1), P(x["最大浮虧"], 1)])
        return tbl(["格", "筆數", "觸及強平筆數（m 0.5%／1%／2%）", "最近一次距強平（m 2%；負＝已穿過）", "單筆期間最大浮虧（價格）"], rows)

    def overlap(src):
        o = src["計畫重疊"]["BTC_W2"]
        return tbl(["2024～2026-10-09 持倉日", "日低 ≤ 72,000", "≤ 66,000", "≤ 58,625", "≤ 54,000", "收盤 < 58,625（A1）", "B3／B4（2029 起才生效）", "收盤 < 200 日線（B4 條件本身）"],
                   [[o["持有日數"], o["日低≤72,000"], o["日低≤66,000"], o["日低≤58,625"], o["日低≤54,000"], o["收盤<58,625（A1）"], o["B3_B4重疊（2029起才生效）"], o["收盤<200日線（B4條件本身，描述）"]]])

    nb_rows = []
    for _, r in NB.iterrows():
        nb_rows.append([f'{r["量倍數"]}', f'{r["漲幅"] * 100:.0f}%', r["出場"] + ("（主格）" if r["主格"] else ""),
                        P(r["BTC_W1"]), P(r["BTC_W2"]), P(r["BTC_early_bitstamp"]), P(r["8幣合併"])])
    nb_t = tbl(["量倍數", "漲幅", "出場", "BTC 2018～2023", "BTC 2024～", "早年（替代）", "8 幣合併"], nb_rows)
    F = J["資金費"]
    lq_lit = J["強平_5倍逐倉"]; lq_mx = D["強平_5倍逐倉"]

    body = f"""
<h1>C17 爆量大漲開多：獨立重跑</h1>
<div class="box"><b>⚠ 2026-10-11 更正（裁定 seq333／seq334）</b>：出場讀法已定為 max（任一條跌破就出）；早年格不可判定 ⇒ 不標暫定、只記前瞻。使用者只算 BTC、用幣本位全倉 ⇒ 本頁的 U 本位 5 倍逐倉強平與 8 幣數字<b>撤回、不當給使用者的結果</b>（8 幣只當旁證）。給使用者的重報見 <a href="C17_BTC幣本位.html">C17_BTC幣本位.html</a>。</div>
<p class="sub">PREREGC17 v1（sha 6fd7cca8b425a8c5）｜裁定 seq330｜回測線｜讀法寫死 {html.escape(J["讀法寫死"])}｜獨立結果 v1 寫檔 {html.escape(J1["寫檔時間"])}｜v2（補 2019-09-10 起資金費）寫檔 {html.escape(J["寫檔時間"])}｜讀登錄 §五 2026-10-11 00:48（台北）｜資料 main {R.SHA[:10]}</p>

<div class="box key">
<h2>結論</h2>
<p><b>出口 ③：先對帳。</b>照登錄字面跑出來的數字，和加密線 §五 對不上：2024 年後的 BTC 和 8 幣方向相反，差距遠超過 0.05%／天。</p>
<p><b>差異原因幾乎可以確定是出場規則的讀法。</b>登錄寫「收盤 &lt; min(訊號日最低價, 前 10 日最低價) 才出場」。照字面取兩者中較低的那條，出場線永遠不會高過訊號日低點，一筆單常常一抱好幾年（BTC 有一筆抱了 1,777 天），持倉日佔窗內八到九成以上。
加密線的數字對得上的是另一種讀法：<b>兩條任一條跌破就出場</b>（等於取 max）。照這個讀法重算後，BTC 兩窗加 8 幣共 10 項，每一項都在 0.05%／天以內、方向全部相同，筆數也對得上（BTC 2018～2023：16 對 17 筆，中位持有 28 對 29 天）。</p>
<p>兩種讀法的判定結果不同，要等裁定線決定登錄要照哪一種讀：</p>
<ul>
<li><b>照字面（min）</b>：BTC 2018～2023 {P(M["BTC_W1"]["每天多賺"])}、2024～ {P(M["BTC_W2"]["每天多賺"])}、早年替代 {P(M["BTC_early_bitstamp"]["每天多賺"])}、8 幣合併 {P(M["8幣合併"]["每天多賺"])}（假訊號 p {J["對照"]["8幣合併"]["假訊號p"]:.2f}）。三項 ≤ 0，屬於出口 ②，測不出。</li>
<li><b>照任一條破就出（max，只當對帳診斷）</b>：BTC 2018～2023 {P(Dm["BTC_W1"]["每天多賺"])}（p {D["對照"]["BTC_W1"]["假訊號p"]:.3f}）、2024～ {P(Dm["BTC_W2"]["每天多賺"])}（p {D["對照"]["BTC_W2"]["假訊號p"]:.2f}）、早年替代 {P(Dm["BTC_early_bitstamp"]["每天多賺"])}、8 幣合併 {P(Dm["8幣合併"]["每天多賺"])}（假訊號 p {D["對照"]["8幣合併"]["假訊號p"]:.3f}）。四項都 &gt; 0、合併 p &lt; 0.05，符合出口 ① 的形狀，最多只能標「暫定成立（探索後）」。但 2024 年後只多 {P(Dm["BTC_W2"]["每天多賺"])}，幾乎是 0；早年那一格用的是替代資料。</li>
</ul>
<p><b>使用者判準（對同窗一直抱 BTC 現貨）</b>：兩種讀法都是 2018～2023 合格、2024～2026 <b>不合格</b>。</p>
<p><b>強平風險</b>：用使用者現行的 5 倍槓桿、逐倉計算。照字面讀法，BTC 8 筆裡有 3 筆碰到強平，原因多半是抱得太久，資金費把保證金慢慢吃光。照 max 讀法，BTC 25 筆裡有 1 筆碰到（2020-03-14 進場，3/16 就碰到，當時最大浮虧 −20.3%）；8 幣 288 筆裡有 60 筆碰到（m＝2%）。<b>5 倍逐倉只要跌約 18～20% 就會被強平；資金費和維持保證金還會讓強平價越來越近。</b></p>
<p><b>和使用者現行計畫的關係</b>：⛔ 不改囤幣，也不改 B3／B4 賣幣。B3、B4 要到 2029 年才生效，所以歷史上沒有重疊的日子。2024～2026 的持倉日和買點價位重疊的天數列在第 4 節。</p>
<p class="muted">⛔ 本頁不是買賣建議，也不談「開幾倍安全」。N 加密帳 ＋82（裁定已定）。乾淨的證據只會來自 2026-10-12 起的前瞻紀錄。</p>
</div>

<h2>1. 獨立結果：照登錄字面（出場取 min）</h2>
<p class="muted">v1（讀 §五 之前寫檔）用的資金費從 2020-01-01 起；v2 把 2019-09-10～12-31 也補進來。只有資金費這一項不同，表中是 v2。v1→v2：BTC 2018～2023 {P(J1["主格"]["BTC_W1"]["每天多賺"])}→{P(M["BTC_W1"]["每天多賺"])}、8 幣合併 {P(J1["主格"]["8幣合併"]["每天多賺"])}→{P(M["8幣合併"]["每天多賺"])}，其他格不變。</p>
<p>每天多賺＝持倉日每日淨報酬的平均，減去同窗所有日子報酬的平均。主臂是 t＋1 開盤進場、每邊成本 0.1%，再扣資金費。p 值是單尾，各做 2,000 次。</p>
{tbl(head4, four(J))}
<p class="muted">持倉比例：BTC 2018～2023 {P(M["BTC_W1"]["持有比例"], 0, False)}、2024～ {P(M["BTC_W2"]["持有比例"], 0, False)}、8 幣各 93～98%。照字面幾乎等於一直抱著。窗尾仍持有的件數：BTC 兩窗各 1 筆，8 幣各 1 筆。
t 收盤進場（敏感度）和主臂的差在 0.001%／天以內。各幣改用自己的資金費時，8 幣合併為 {P(J["敏感度_各幣自己資金費"]["8幣合併"])}；BTC 改用幣本位資金費時，兩窗分別為 {P(J["敏感度_幣本位資金費"]["BTC_W1"])}、{P(J["敏感度_幣本位資金費"]["BTC_W2"])}。</p>

<h2>2. 對帳（讀 §五 之後才做；t 收盤進場，對齊 §五 的口徑）</h2>
{rec_t}
<p class="muted">max 讀法和 §五 的最大差是 {maxdiff * 100:.3f}%／天，回測的數字多數比 §五 稍低一點（只有 BNB 稍高）。可能原因：資金費的算法不同（回測在 2018～2019 沒有資料的期間用年化 10% 代入，2020 年後用實際值），或成本的扣法不同。
其他候選原因都排除了：進場時點（t 收盤和 t＋1 開盤的差 ≤ 0.001%）；只看前 10 日低點（2024 年後變成負的）；只看訊號日低點（和字面讀法幾乎一樣）。
固定 14 天（描述）：回測 BTC 兩窗 {P(float(NB[NB["出場"] == "fixed14"]["BTC_W1"].iloc[0]))}／{P(float(NB[NB["出場"] == "fixed14"]["BTC_W2"].iloc[0]))}，§五 為 +0.28%／+0.19%，第二窗差 0.06%，超過 0.05%。
早年 BTC 訊號後 14 天比全部日多 {P(RC["早年_訊號後14天_減_全部日"], 1)}（Bitstamp，{RC["早年_訊號天數"]} 個訊號日），§五 為 +12.0%（Coin Metrics）；兩邊資料來源不同。</p>

<h2>3. 使用者判準（主臂 1 倍，對同窗一直抱 BTC 現貨）</h2>
<h3>照字面（min）</h3>{crit(J)}
<h3>任一條破就出（max；對帳診斷）</h3>{crit(D)}
<p class="muted">合格＝年化比抱 BTC 高，而且年化÷|MDD| 也不比抱 BTC 低；另列＝只有年化比較高；不合格＝其餘。主臂以全部資金當名目，空手時現金報酬算 0%。</p>

<h2>4. 合約風險：5 倍逐倉的強平</h2>
<p>使用者現行槓桿是 5 倍（加密線現況：BTCUSD 幣本位全倉 5 倍多單；SOL 提醒也設 5 倍）。這裡每筆用 5 倍逐倉計算：保證金＝名目的 1/5，先扣 0.1% 進場費，每天再扣當天的資金費，然後算強平價 Lp＝進場價 ×（1 − 剩餘保證金）÷（1 − 維持保證金率 m），用現貨日低判斷有沒有碰到。</p>
<h3>照字面（min）</h3>{liq(J)}
<h3>任一條破就出（max；對帳診斷）</h3>{liq(D)}
<p class="muted">BTC 標記價日低（2020 年起）的結果和現貨日低相近：字面讀法 W1／W2 觸及 {lq_lit["BTC_W1"]["標記價_觸及筆數_m0.02"]}／{lq_lit["BTC_W2"]["標記價_觸及筆數_m0.02"]} 筆，max 讀法 {lq_mx["BTC_W1"]["標記價_觸及筆數_m0.02"]}／{lq_mx["BTC_W2"]["標記價_觸及筆數_m0.02"]} 筆。
使用者實際用的是全倉，帳戶裡其他餘額會撐住保證金，所以逐倉是比較嚴的算法。LINK 在 2020-03-12 有一根現貨日低 0.0001 的插針，所以 LINK 的最大浮虧接近 −100%。
5 倍、每筆用全部資金當保證金（描述）：BTC 2018～2023 兩種讀法都會因為一筆強平而歸零；2024～ 字面讀法也會歸零，max 讀法年化 {P(lq_mx["BTC_W2"]["5倍全資金權益_描述"]["年化"], 1)}。</p>

<h2>5. 與現行計畫重疊的天數（只報、不改計畫）</h2>
<h3>照字面（min）</h3>{overlap(J)}
<h3>任一條破就出（max）</h3>{overlap(D)}
<p class="muted">買點是 72,000（只買現貨）、66,000、58,625、54,000，都是 2026 年訂的價位，所以只有 2024 年後這個窗有意義。2018～2023 整段價格都在這些價位以下，重疊天數沒有意義，不列。</p>

<h2>6. 資金費</h2>
<p>BTCUSDT 永續資金費的實際值從 {F["BTCUSDT首筆"]} 到 {F["BTCUSDT末筆"]}（主檔 2020-01-01 起，加上資料庫 1011-0044 新補的 2019-09-10～12-31，兩段接起來是連續的）。2019-09-10 以前永續合約還不存在，2026-10-01 起的月封存還沒發布，這兩段都照登錄以年化 10% 代入：2018～2023 窗共 {F["W1代入天數"]} 天（2018-01-01～2019-09-09）、2024～ 窗共 {F["W2代入天數"]} 天（2026-09-30～10-09）、早年全部代入。有資料的日子裡，每天都剛好 3 筆，沒有例外。
實際年化：2019-09～2023 為 {P(F["W1實際年化（覆蓋日）"], 1, False)}，2024～2026-09 為 {P(F["W2實際年化（覆蓋日）"], 1, False)}。</p>

<h2>7. 鄰格（描述，不判、不計 N；照字面主格的訊號與出場）</h2>
{nb_t}
<p class="muted">照字面讀法時，前 5／10／20 日低點這三格都幾乎一直抱著。均線、最高收盤回落、固定天數這幾種出場比較短，數字是正的；但這些格子在登錄裡只當描述。</p>

<h2>8. 偏離、限制、補讀法</h2>
<ul>
<li><b>早年 BTC 格</b>：登錄指定 Coin Metrics 的 PriceUSD 加 volume_reported_spot_usd_1d，但資料庫的私有 coinmetrics 檔沒有量的欄位，也沒有日高低，所以照登錄算不出來，<b>待資料庫補</b>。這裡改用私有 Bitstamp 2013-01-21～2017-08-16 的日 K（量＝BTC 量 × 收盤）跑替代版，只當描述，不當判定。原始資料不進 repo，只放彙總。</li>
<li>8 幣的資金費：照登錄字面一律用 BTCUSDT（敏感度改用各幣自己的資金費，見第 1 節）。各幣剔除上市後前 30 根 K 棒。8 幣合併是把所有持倉日等權平均。</li>
<li>兩個窗各自獨立跑，窗外的訊號不帶進來；窗尾還在持有的部位以窗尾收盤估值，不扣平倉費。</li>
<li>幣池是 2026-09 的快照，早年有倖存者偏差；Binance 現貨以 USDT 計價。</li>
<li>--check：fixture 4 個（均量不含 t、次日開盤平倉、資金費毫秒尾數歸日、持倉中不重設），每個都附會變紅的反例。另外用一支純迴圈的參考實作重算 {CK["比對次數"]} 項（主格加隨機抽 6 個鄰格 × 11 個單位、21 次平移、300 天資金費歸日），<b>不同 {CK["不同數"]} 項</b>，最大差 {CK["最大差"]:.1e}。</li>
</ul>

<h2>9. 前瞻</h2>
<p>從 2026-10-12 起，每出現一次 BTC 訊號就記一筆（不交易也記），格式見 <code>resultsC17/forward_template.csv</code>。2026-10-01 起的資金費月封存還沒發布，前瞻用到時照實寫明代入或缺。出場讀法還在對帳，所以兩種讀法的出場都記，裁定後只取其中一欄來判。累積 20 筆再判，到時 N 只計前瞻這一格。</p>
"""
    css = """
:root{--bg:#fbfbfa;--fg:#1d1d1f;--mut:#5f6368;--line:#dcdcdc;--acc:#0b5cad;--keybg:#eef4fb}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]){--bg:#161618;--fg:#ececec;--mut:#a3a3a3;--line:#3a3a3c;--acc:#7cb4ff;--keybg:#1e2a38}}
:root[data-theme="dark"]{--bg:#161618;--fg:#ececec;--mut:#a3a3a3;--line:#3a3a3c;--acc:#7cb4ff;--keybg:#1e2a38}
body{background:var(--bg);color:var(--fg);font-family:-apple-system,"Noto Sans TC","Microsoft JhengHei",sans-serif;line-height:1.65;margin:0;padding:0 16px 48px;max-width:980px;margin:auto}
h1{font-size:1.5rem;margin:24px 0 4px}h2{font-size:1.15rem;margin:28px 0 8px;border-bottom:1px solid var(--line);padding-bottom:4px}h3{font-size:1rem;margin:16px 0 6px}
.sub,.muted{color:var(--mut);font-size:.88rem}.box{border:1px solid var(--line);border-radius:8px;padding:12px 16px;margin:16px 0}.key{background:var(--keybg)}
.tw{overflow-x:auto;margin:8px 0}table{border-collapse:collapse;font-size:.88rem;min-width:100%}th,td{border:1px solid var(--line);padding:4px 8px;text-align:right;white-space:nowrap}
th{background:transparent;color:var(--mut);font-weight:600}td:first-child,th:first-child{text-align:left}code{font-size:.85em}
"""
    page = f'<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>C17 爆量大漲開多</title><style>{css}</style></head><body>{body}</body></html>'
    with open(os.path.join(OUT, "C17爆量大漲開多.html"), "w", encoding="utf-8") as f:
        f.write(page)
    print("page OK", round(maxdiff * 100, 4))




def main_cm():
    J = json.load(open(os.path.join(OUT, "btc_coinm.json"), encoding="utf-8"))
    CK = json.load(open(os.path.join(OUT, "check_btccm.json"), encoding="utf-8"))
    W1, W2 = J["窗"]["2018～2023"], J["窗"]["2024～2026-10-09"]

    def btc(x):
        return f"{x:+.5f}"

    def row(lab, x):
        u, h = x["USD_囤幣加訊號"], x["USD_只囤幣"]
        dd = x.get("最低點還要再跌才強平")
        liq = (f'碰到（{x["強平日"]}）' if x["強平日"] else (f"沒碰到；最接近時還要再跌 {dd * 100:.0f}%" if dd is not None else "沒碰到"))
        return [lab, btc(x["對只囤幣增減BTC"]), P(x["增減÷W0"], 1), P(u["年化"], 1), f'{u["年化÷|MDD|"]:.2f}', P(h["年化"], 1), f'{h["年化÷|MDD|"]:.2f}', f'<b>{x["使用者判準"]}</b>', liq]

    head = ["", "對只囤幣增減（BTC）", "÷ 錢包 0.0715", "USD 年化", "年化÷|MDD|", "只囤幣年化", "只囤幣 年化÷|MDD|", "判準", "強平"]
    t1 = tbl(head, [row("3 張", W1["3張"]), row("24 張", W1["24張"]), row("3 張（按今日比例）", W1["3張_按今日比例"]), row("24 張（按今日比例）", W1["24張_按今日比例"])])
    t2 = tbl(head, [row("3 張", W2["3張"]), row("24 張", W2["24張"]), row("3 張（按今日比例）", W2["3張_按今日比例"]), row("24 張（按今日比例）", W2["24張_按今日比例"])])

    def years(w):
        ks = ["3張", "24張", "24張_按今日比例"]
        ys = [y["年"] for y in w["3張"]["逐年"]]
        rows = []
        for i, y in enumerate(ys):
            rows.append([y] + [f'{w[k]["逐年"][i]["判"]}（{btc(w[k]["逐年"][i]["增減BTC"])}）' for k in ks])
        return tbl(["年", "3 張", "24 張", "24 張（按今日比例）"], rows)

    lq = J["現況強平價_本模型"]
    body = f"""
<h1>C17 爆量大漲開多：只算 BTC、幣本位</h1>
<p class="sub">裁定 seq333（出場讀法定 max）＋ seq334（照使用者實際做法重報，描述、N 不變）｜回測線｜讀法寫死 {html.escape(J["讀法寫死"])}｜寫檔 {html.escape(J["寫檔時間"])}｜資料 main {R.SHA[:10]}</p>
<div class="box key">
<h2>結論</h2>
<p><b>近兩年沒有提升。</b>2024-01-01～2026-10-09，「囤幣＋訊號時開幣本位多」和「只囤幣」比，3 張只多 {btc(W2["3張"]["對只囤幣增減BTC"])} BTC（錢包的 {P(W2["3張"]["增減÷W0"], 2)}），24 張只多 {btc(W2["24張"]["對只囤幣增減BTC"])} BTC（{P(W2["24張"]["增減÷W0"], 1)}）。逐年看，2024 年扣分、2025 年加分、2026 年扣分。每天多賺 {P(W2["每天多賺_幣本位資金費(1單位名目)"])}，假訊號 p {W2["假訊號p"]:.2f}，和假訊號分不出來。</p>
<p><b>2018～2023 有提升，但要看張數。</b>3 張：錢包從 0.0715 BTC 變成 {W1["3張"]["窗末錢包權益BTC"]:.4f} BTC（{P(W1["3張"]["增減÷W0"], 0)}），USD 年化 {P(W1["3張"]["USD_囤幣加訊號"]["年化"], 1)}，只囤幣是 {P(W1["3張"]["USD_只囤幣"]["年化"], 1)}，合格。<b>24 張在 2018-12-21 被強平，錢包歸零</b>：當年 BTC 只有 3,000～4,000 美元，24 張（2,400 美元）約等於錢包價值的 8 倍。若按今天的比例（24 張約為錢包價值的 0.41 倍）換算，就不會碰到強平，錢包 +{P(W1["24張_按今日比例"]["增減÷W0"], 0, False)}。</p>
<p><b>強平風險</b>：以使用者錢包 0.0715 BTC、全倉、維持保證金率 0.4%（幣安第 1 級）計算。2024 年後 3 張和 24 張都沒碰到強平，最接近的一次還要再跌 {W2["3張"]["最低點還要再跌才強平"] * 100:.0f}%（3 張）、{W2["24張"]["最低點還要再跌才強平"] * 100:.0f}%（24 張）。2018～2023 的 3 張也沒碰到（最接近時還要再跌 {W1["3張"]["最低點還要再跌才強平"] * 100:.0f}%）；24 張在 2018 年碰到。</p>
<p class="muted">⛔ 不是買賣建議，也不談「開幾張安全」。早年格不可判定 ⇒ 不標暫定，只記前瞻（2026-10-12 起，滿 20 筆再判）。⛔ 不改囤幣與 B3／B4 賣幣計畫。</p>
</div>

<h2>1. 2024-01-01～2026-10-09（8 筆）</h2>{t2}
<h2>2. 2018～2023（17 筆）</h2>{t1}
<p class="muted">USD 年化以「錢包權益 × BTC 收盤」計，MDD 用每日收盤。判準：合格＝年化比只囤幣高，而且年化÷|MDD| 也不比只囤幣低；另列＝只有年化比較高。
「按今日比例」：每筆名目＝k × 0.0715 × 進場價，k＝張數×100 ÷（0.0715 × 2026-10-09 收盤 82,636）；3 張 k≈0.051，24 張 k≈0.41。這一列只是描述。</p>
<h2>3. 逐年加分或扣分（錢包 BTC 增減）</h2>
<h3>2018～2023</h3>{years(W1)}
<h3>2024～</h3>{years(W2)}

<h2>4. 口徑與限制</h2>
<ul>
<li>訊號與出場：成交量 ＞ 前 20 日平均量的 2 倍，且漲幅 ＞ 5% ⇒ 次日開盤開多；收盤 ＜ max(訊號日最低, 前 10 日最低) ⇒ 次日開盤平倉（seq333）。價格用 Binance 現貨 BTCUSDT；幣本位永續和現貨的價差沒算。</li>
<li>部位：每次訊號開 3 張或 24 張 BTCUSD 幣本位永續（每張 100 USD），保證金是合約錢包。兩個窗都各自從 0.0715 BTC 起算。使用者現有的 3 張常駐多單沒有併進來；如果同一個錢包同時抱著常駐單，強平會更近。</li>
<li>成本：每邊 0.1%。資金費用幣本位 BTCUSD 實際值（{J["CM資金費起訖"][0]}～{J["CM資金費起訖"][1]}；2026-06-30 少一筆是官方本來就沒有）。沒有資料的日子以年化 10% 代入：2018～2023 窗 {W1["窗內資金費代入天數"]} 天（其中持倉日 {W1["持有日資金費代入天數"]} 天）、2024～ 窗 {W2["窗內資金費代入天數"]} 天（持倉日 {W2["持有日資金費代入天數"]} 天）。</li>
<li>強平：權益（BTC）＝錢包 ＋ 名目 ×（1/進場價 − 1/價格），權益 ≤ 0.4% × 名目 ÷ 價格 就強平。用現貨日低判斷；改用幣本位標記價日低（2020-08 起），結果一樣。分級表用的是 2026-05 的現值，早年的實際分級可能不同。
本模型算出使用者現況的強平價：3 張 @84,500 為 {lq["3張@84,500"]:,.0f}（幣安顯示 3,591）；加滿 24 張約 {lq["24張(3@84,500+10@66,000+11@58,625)"]:,.0f}（加密線估約 22,000）。實際以幣安顯示為準。</li>
<li>旁證（⛔ 不進結果句）：8 幣合併（max 讀法）每天多賺 {P(J["旁證_8幣合併_max_v2"]["每天多賺"])}，p {J["旁證_8幣合併_max_v2"]["假訊號p"]:.3f}。</li>
<li>--check：另外寫一支程式重算（強平改用不等式逐日直接判斷、資金費改用 datetime 逐筆歸日、交易清單用純迴圈），比對 {CK["比對次數"]} 項，<b>不同 {CK["不同數"]} 項</b>；強平公式的 fixture 附會變紅的反例。</li>
</ul>
"""
    css = """
:root{--bg:#fbfbfa;--fg:#1d1d1f;--mut:#5f6368;--line:#dcdcdc;--keybg:#eef4fb}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]){--bg:#161618;--fg:#ececec;--mut:#a3a3a3;--line:#3a3a3c;--keybg:#1e2a38}}
:root[data-theme="dark"]{--bg:#161618;--fg:#ececec;--mut:#a3a3a3;--line:#3a3a3c;--keybg:#1e2a38}
body{background:var(--bg);color:var(--fg);font-family:-apple-system,"Noto Sans TC","Microsoft JhengHei",sans-serif;line-height:1.65;padding:0 16px 48px;max-width:980px;margin:auto}
h1{font-size:1.5rem;margin:24px 0 4px}h2{font-size:1.15rem;margin:28px 0 8px;border-bottom:1px solid var(--line);padding-bottom:4px}h3{font-size:1rem;margin:16px 0 6px}
.sub,.muted{color:var(--mut);font-size:.88rem}.box{border:1px solid var(--line);border-radius:8px;padding:12px 16px;margin:16px 0}.key{background:var(--keybg)}
.tw{overflow-x:auto;margin:8px 0}table{border-collapse:collapse;font-size:.88rem;min-width:100%}th,td{border:1px solid var(--line);padding:4px 8px;text-align:right;white-space:nowrap}
th{color:var(--mut);font-weight:600}td:first-child,th:first-child{text-align:left}
"""
    page = f'<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>C17 BTC 幣本位</title><style>{css}</style></head><body>{body}</body></html>'
    with open(os.path.join(OUT, "C17_BTC幣本位.html"), "w", encoding="utf-8") as f:
        f.write(page)
    print("page_cm OK")
if __name__ == "__main__":
    main()
    main_cm()

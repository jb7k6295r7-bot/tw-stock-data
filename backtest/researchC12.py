# -*- coding: utf-8 -*-
"""PREREGC12「價格區間預測準不準（機率區間的校準檢驗）v1」（sha 84310aa20866d282）——回測線執行端。裁定 seq292：核准，N＝108（T1、T2 都判）。

⭐ 讀法寫死：2026-10-04 13:11（台北，腳本 TZ=Asia/Taipei date 取得）——⛔ 在算出任何數字之前寫在這裡；之後只准補「執行時發現」並標時間。
   登錄沒寫到、由回測線補的讀法標【執行者補】。

資料：市場資料庫/虛擬貨幣/data/crypto 是 main 的唯讀鏡像；本支讀同一 main commit 1fb8815e81 的 git archive 副本（~/c10data/<sha>/data/crypto），
   --check 逐檔比對兩者位元組相同。6 幣現貨日 K：BTC 2013-01-01、ETH 2017-08-17、BNB 2017-11-06、SOL 2020-08-11、XRP 2018-05-04、DOGE 2019-07-05 起（各幣窗起點不同，照實報）
   窗尾 2026-09-30（登錄 §二）；日 K 必須逐日無缺，否則停

⭐ 落地讀法
 Q1 起點（登錄 §二）：第一個起點＝資料起點＋730 天（日曆日＝列數，日 K 無缺）；之後每 h 天一個（不重疊）；最後一個起點要看得到完整 h 天（起點＋h ≤ 2026-09-30）
 Q2 日對數報酬 r_t＝ln(C_t / C_{t−1})；「起點當日收盤以前」＝含起點當天收盤 C_s、不含之後
 Q3 M1：σ＝r_{s−89..s}（90 個）的樣本標準差（ddof＝1）【執行者補：ddof】；區間＝P0·exp(±zσ√h)，漂移 0；z＝1.645（90%）、1.2816（80% 描述）
 Q4 M3（RiskMetrics 1996，λ＝0.94，零均值）：σ²_t＝λσ²_{t−1}＋(1−λ) r_t²；初值＝前 30 個 r² 的平均【執行者補：初值；730 天暖機後影響 ≈ 0.94^700】；用 σ_s（含 r_s）
 Q5 M2（擴張窗）：起點以前全部 h 天對數報酬 ln(C_{t+h}/C_t)，t＋h ≤ s（兩端都在起點當天以前；重疊窗）【執行者補：重疊取樣】；
    T1 取 5%／95% 分位（80% 描述取 10%／90%），numpy 線性內插；
    T2 下緣＝起點以前全部「h 天內途中最低跌幅」min(low_{t+1..t+h})/C_t − 1（t＋h ≤ s）的 5% 分位，下緣＝P0×(1＋該分位)
 Q6 T1 命中：下緣 ≤ C_{s+h} ≤ 上緣；T2 命中：min(low_{s+1..s+h}) ≥ 單邊 95% 下緣（M1／M3：P0·exp(−1.645σ√h)，⚠ 依構造偏窄、故意保留）
    「起點後 h 天內」＝s＋1～s＋h 那 h 根（起點當天的 low 發生在起點收盤之前，不算）【執行者補】
 Q7 CI：命中序列（0／1，依起點時間排）做 stationary block bootstrap，L＝Politis–White（researchc1，同一支），2,000 次，每格種子 20260923；
    信賴水準 1−0.05/108 ⇒ 取第 0.05/216 與 1−0.05/216 百分位（numpy 線性內插；2,000 次下近似最小／最大值，列為限制）；命中序列全 1 或全 0 ⇒ CI＝點估計
 Q8 判準（登錄 §三）：容忍帶 T1 80～100%、T2 85～100%。依登錄列的順序判：
    ① CI 整條在容忍帶內 ⇒ 判過 ② CI 上界 < 名目 ⇒ 偏窄 ③ CI 下界 > 名目 ⇒ 偏寬 ④ 其他 ⇒ 測不出
    兩條同時成立時（例：在帶內且上界 < 名目）以先列者為準，另加註「略窄／略寬（在容忍帶內）」【執行者補：重疊時的優先序】
 Q9 描述（不判）：① 80% 中央區間 T1 命中 ② 200 日線（含起點的近 200 日收盤均）、200 週線（近 1,400 日）當下緣：只算起點收盤在均線之上的起點，h 天內 low 跌破均線的比例；
    另報起點已在均線之下的比例【執行者補：均線之下的起點不算「下緣」】③ 逐年（起點年份）命中率；含 2020-03-12、2022-05-09～06-18、2022-11-08～09、2025-10-10 的 h30 起點，列區間與實際
    ④ 沒守住時平均跌破多少：T2＝mean(min low ÷ 下緣 − 1)；T1 跌出下緣者同法
 Q10 先驗對答：
    ① T2 的 M1／M3（6 幣 × 3h × 2 模型＝36 格）偏窄 > 18 格 ⇒ 中【執行者補：「多數」＝過半】
    ② T1 h7：|c_M3 − 90%| < |c_M1 − 90%| 的幣 ≥ 4 ⇒ 中【執行者補】
    ③ T1 h30 M2 至少一幣偏窄 ⇒ 中
    ④ 200 日線當下緣，6 幣合併、每個 h 的跌破比例都 ≥ 15%（名目 5% 的 3 倍）⇒ 中【執行者補：「遠高於」＝≥3 倍】
 Q11 --check：fixture a～d（登錄 §十②）各附會紅的反例：a M1 常數報酬 ⇒ 區間退化為 P0（反例：用到起點之後的資料）；另驗 M3 同理；
    b 起點不重疊（反例：重疊）；c T2 用 low 的最小值（反例：用 close）；d M2 只含起點以前（反例：全期分位）；
    再用逐列純迴圈的參考實作抽樣重算命中（種子 20260923），逐位比；鏡像與副本逐檔比對
⛔ 結果句只說「區間大小準不準」：⛔ 不寫能預測漲跌方向、⛔ 不寫某價位是底、⛔ 不用下緣推倍數。

〔補檢 2026-10-04 18:40（台北，TZ=Asia/Taipei date；裁定 seq293 §一）〕
 Q12 判過要同時符合：① bootstrap CI 在容忍帶內（Q8 原條件）② Clopper-Pearson 精確區間（信賴水準 1−0.05/108，雙尾各 0.05/216）也在容忍帶內。只降不升。
     Clopper-Pearson：以確切命中數 x／起點數 n，用二項分配 CDF 二分法解（不裝 scipy）：下界解 P(X ≥ x; p)＝α/2、上界解 P(X ≤ x; p)＝α/2；x＝0 下界 0、x＝n 上界 1
     被降級的格：偏窄＝bootstrap 與 CP 上界都 < 名目；偏寬＝兩者下界都 > 名目；否則測不出（同 C12b 的「兩者都」寫法，避免只靠 bootstrap 就升成偏窄／偏寬）【執行者補】
     原本不是判過的格一律不動（只降不升）；cells.csv 加欄：命中數、CP下、CP上、原判（補檢前）、判定（補檢後）、補檢降級
 新增 fixture f：Clopper-Pearson（x＝n ⇒ 上界 1、下界＝(α/2)^(1/n)；x＝0 ⇒ 上界＝1−(α/2)^(1/n)；另與已知值比對），反例＝常態近似（Wald）
"""
from __future__ import annotations
import os, sys, json, time, math, argparse, html, hashlib
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
import researchc1 as C1

SHA = "1fb8815e81aa53edf91aacb8ebb4125c716ead3f"
ROOT = os.path.expanduser(f"~/c10data/{SHA}/data/crypto")
MIRROR = "/mnt/c/SynologyDrive/投資/市場資料庫/虛擬貨幣/data/crypto"
REPO = os.path.expanduser("~/tw-p17")
OUT = os.path.join(REPO, "backtest", "resultsC12")
COINS = ("BTC", "ETH", "BNB", "SOL", "XRP", "DOGE")
HS = (7, 30, 90)
MODELS = ("M1", "M3", "M2")
MODEL_ZH = {"M1": "M1 近90日波動", "M2": "M2 經驗分位", "M3": "M3 EWMA"}
TARGETS = ("T1", "T2")
NOM = {"T1": 0.90, "T2": 0.95}
BAND = {"T1": (0.80, 1.00), "T2": (0.85, 1.00)}
Z90, Z80 = 1.645, 1.2816
W_END = "2026-09-30"
WARM = 730
LAM = 0.94
N_CELLS = 108
SEED = 20260923
N_BOOT = 2000
FROZEN = "2026-10-04 13:11（台北）"
EVENTS = {"2020-03-12": ("2020-03-12", "2020-03-12"), "2022 LUNA": ("2022-05-09", "2022-06-18"), "2022 FTX": ("2022-11-08", "2022-11-09"), "2025-10-10": ("2025-10-10", "2025-10-10")}


# ───────────────────────── 資料與模型 ─────────────────────────
def load(sym, root=ROOT):
    d = pd.read_csv(os.path.join(root, f"{sym}.csv"), dtype={"date": str}).drop_duplicates("date").sort_values("date").reset_index(drop=True)
    d = d[d["date"] <= W_END].reset_index(drop=True)
    assert d["date"].iloc[-1] == W_END, (sym, d["date"].iloc[-1])
    gap = (pd.to_datetime(d["date"].iloc[-1]) - pd.to_datetime(d["date"].iloc[0])).days + 1
    assert gap == len(d), f"⛔ {sym} 現貨日 K 有缺日"
    return {"sym": sym, "dates": d["date"].to_numpy(), "close": d["close"].to_numpy(float), "low": d["low"].to_numpy(float)}


def logret(c):
    r = np.full(len(c), np.nan); r[1:] = np.diff(np.log(c)); return r


def starts_of(n, h, mut=None):
    """Q1：第一個起點索引 730，之後每 h 天；起點＋h ≤ n−1。mut＝overlap ⇒ 每天一個（反例）。"""
    step = 1 if mut == "overlap" else h
    return np.arange(WARM, n - h, step)


def sigma_m1(c, s, mut=None):
    r = logret(c)
    hi = s + 5 if mut == "future" else s          # 反例：用到起點之後
    w = r[hi - 89:hi + 1]
    return float(np.std(w, ddof=1))


def ewma_var(c):
    r = logret(c); v = np.full(len(c), np.nan)
    v0 = float(np.mean(r[1:31] ** 2)); prev = v0
    for t in range(1, len(c)):
        prev = LAM * prev + (1 - LAM) * r[t] ** 2 if t > 30 else v0
        v[t] = prev
    return v


def sigma_m3(c, s, mut=None, ev=None):
    v = ewma_var(c) if ev is None or mut == "future" else ev
    k = min(s + 5, len(c) - 1) if mut == "future" else s       # 反例：用到起點之後
    return float(math.sqrt(v[k]))


def path_min_ret(c, low, h):
    """mdd[t]＝min(low_{t+1..t+h}) / C_t − 1（t＋h 超出 ⇒ NaN）。"""
    n = len(c); out = np.full(n, np.nan)
    lw = pd.Series(low).rolling(h).min().to_numpy()          # lw[k]＝min(low[k−h+1..k])
    out[: n - h] = lw[h:] / c[: n - h] - 1.0
    return out


def m2_bounds(c, low, s, h, mut=None, pm=None):
    """Q5：回 (T1 下, T1 上, 80% 下, 80% 上, T2 下)。mut＝full ⇒ 用全期（反例）。"""
    lc = np.log(c)
    hr = lc[h:] - lc[:-h]                                     # hr[t]＝ln(C_{t+h}/C_t)
    pm = path_min_ret(c, low, h) if pm is None else pm
    if mut == "full":
        H = hr; P = pm[np.isfinite(pm)]
    else:
        H = hr[: s - h + 1]                                   # t ≤ s−h
        P = pm[: s - h + 1]
    q05, q95, q10, q90 = np.percentile(H, [5, 95, 10, 90])
    p0 = c[s]
    return p0 * math.exp(q05), p0 * math.exp(q95), p0 * math.exp(q10), p0 * math.exp(q90), p0 * (1.0 + float(np.percentile(P, 5)))


def bounds(c, low, s, h, model, mut=None, pm=None, ev=None):
    p0 = c[s]
    if model == "M2":
        return m2_bounds(c, low, s, h, mut, pm)
    sg = sigma_m1(c, s, mut) if model == "M1" else sigma_m3(c, s, mut, ev)
    a = sg * math.sqrt(h)
    return p0 * math.exp(-Z90 * a), p0 * math.exp(Z90 * a), p0 * math.exp(-Z80 * a), p0 * math.exp(Z80 * a), p0 * math.exp(-Z90 * a)


def hits(c, low, s, h, b, mut=None):
    """Q6：回 (T1 命中, T2 命中, 80% 命中, 途中最低, 端點收盤)。mut＝close ⇒ T2 用收盤（反例）。"""
    end = c[s + h]
    pmin = float(np.min(c[s + 1:s + h + 1])) if mut == "close" else float(np.min(low[s + 1:s + h + 1]))
    return (b[0] <= end <= b[1]), (pmin >= b[4]), (b[2] <= end <= b[3]), pmin, end


# ───────────────────────── CI 與判準 ─────────────────────────
def ci_of(x):
    x = np.asarray(x, float); c = float(x.mean())
    if x.min() == x.max():
        return c, c, c, 1
    L = C1.politis_white_block(x)
    rng = np.random.default_rng(SEED)
    bs = np.array([x[C1.stationary_idx(len(x), L, rng)].mean() for _ in range(N_BOOT)])
    a = 0.05 / N_CELLS / 2
    return c, float(np.percentile(bs, 100 * a)), float(np.percentile(bs, 100 * (1 - a))), int(L)


def _binom_cdf(k, n, p):
    """P(X ≤ k)，X ~ Bin(n, p)；log 空間逐項加總。"""
    if k < 0:
        return 0.0
    if k >= n:
        return 1.0
    if p <= 0:
        return 1.0
    if p >= 1:
        return 0.0
    lp, lq = math.log(p), math.log1p(-p)
    terms = [math.lgamma(n + 1) - math.lgamma(i + 1) - math.lgamma(n - i + 1) + i * lp + (n - i) * lq for i in range(k + 1)]
    m = max(terms)
    return min(1.0, math.exp(m) * sum(math.exp(t - m) for t in terms))


def clopper_pearson(x, n, alpha, mut=None):
    """雙尾 1−alpha 精確區間。mut＝wald ⇒ 常態近似（反例）。"""
    if mut == "wald":
        p = x / n; z = 3.5; s = math.sqrt(p * (1 - p) / n)
        return max(0.0, p - z * s), min(1.0, p + z * s)
    a = alpha / 2

    def solve(f):
        lo, hi = 0.0, 1.0
        for _ in range(200):
            mid = (lo + hi) / 2
            if f(mid):
                hi = mid
            else:
                lo = mid
        return (lo + hi) / 2
    lower = 0.0 if x == 0 else solve(lambda p: 1.0 - _binom_cdf(x - 1, n, p) >= a)     # 最小的 p 使 P(X ≥ x) ≥ α/2
    upper = 1.0 if x == n else solve(lambda p: _binom_cdf(x, n, p) <= a)               # 最小的 p 使 P(X ≤ x) ≤ α/2
    return lower, upper


def verdict2(tg, lo, hi, cpl, cpu):
    """Q12：補檢後判定。只降不升。"""
    v = verdict(tg, lo, hi)
    if not v.startswith("判過"):
        return v
    blo, bhi = BAND[tg]
    if cpl >= blo and cpu <= bhi:
        return v
    nom = NOM[tg]
    return "偏窄" if (hi < nom and cpu < nom) else ("偏寬" if (lo > nom and cpl > nom) else "測不出")


def verdict(tg, lo, hi):
    blo, bhi = BAND[tg]; nom = NOM[tg]
    inb = lo >= blo and hi <= bhi
    if inb:
        note = "（略窄，在容忍帶內）" if hi < nom else ("（略寬，在容忍帶內）" if lo > nom else "")
        return "判過" + note
    if hi < nom:
        return "偏窄"
    if lo > nom:
        return "偏寬"
    return "測不出"


# ───────────────────────── fixture ─────────────────────────
def fx_a(mut=None):
    """a. M1（與 M3）：常數報酬序列（每天 +1%）σ＝0 ⇒ 區間退化為 P0；起點之後才出現大波動也不能影響。"""
    n = 900; c = 100 * np.exp(0.01 * np.arange(n)); c[805:] = c[805:] * np.exp(np.random.default_rng(1).normal(0, 0.2, n - 805)).cumprod()
    s = 800; ok = True
    for model in ("M1",):
        b = bounds(c, c, s, 7, model, mut)
        ok &= all(abs(x / c[s] - 1) < 1e-12 for x in (b[0], b[1], b[4]))
    return bool(ok)


def fx_a3(mut=None):
    """a（M3 版）：同上，EWMA 只能用到起點當天。常數報酬 ⇒ r² 恆為 1e-4、σ＝0.01 不變；起點後的大波動不得影響。"""
    n = 900; c = 100 * np.exp(0.01 * np.arange(n)); c2 = c.copy(); c2[805:] = c2[805:] * 3.0
    s = 800
    b1 = bounds(c, c, s, 7, "M3", mut); b2 = bounds(c2, c2, s, 7, "M3", mut)
    return bool(abs(b1[0] - b2[0]) < 1e-9 * c[s] and abs(b1[0] / c[s] - math.exp(-Z90 * 0.01 * math.sqrt(7))) < 1e-9)


def fx_b(mut=None):
    """b. 起點不重疊：相鄰起點差 h，各段 (s, s+h] 不交疊，第一個＝730，最後一個＋h ≤ 末列。"""
    n = 1000; ok = True
    for h in HS:
        st = starts_of(n, h, mut)
        ok &= st[0] == WARM and np.all(np.diff(st) == h) and st[-1] + h <= n - 1 and st[-1] + 2 * h > n - 1
    return bool(ok)


def fx_c(mut=None):
    """c. T2 用 h 天內 low 的最小值：收盤一直在下緣之上、但某天日低跌破 ⇒ 應判「沒守住」。"""
    c = np.full(20, 100.0); low = c.copy(); low[5] = 50.0
    b = (90.0, 110.0, 95.0, 105.0, 80.0)
    t1, t2, _, pmin, _ = hits(c, low, 2, 7, b, mut)
    return bool(t1 and not t2 and pmin == 50.0)


def fx_d(mut=None):
    """d. M2 擴張窗只含起點以前：把起點之後的價格改掉，M2 的區間不能變。"""
    rng = np.random.default_rng(7); n = 1200
    c = 100 * np.exp(np.cumsum(rng.normal(0, 0.02, n))); low = c * 0.99
    c2 = c.copy(); c2[1001:] = c2[1001:] * np.exp(np.cumsum(rng.normal(0, 0.15, n - 1001))); l2 = low.copy(); l2[1001:] = c2[1001:] * 0.99
    b1 = m2_bounds(c, low, 1000, 30, mut); b2 = m2_bounds(c2, l2, 1000, 30, mut)
    return bool(np.allclose(b1, b2, rtol=0, atol=1e-12))


FIXTURES = (("a M1 常數報酬 ⇒ 區間＝P0", fx_a, "future", "用到起點之後 5 天的資料"),
            ("a M3 同理", fx_a3, "future", "EWMA 用到起點之後"),
            ("b 起點不重疊", fx_b, "overlap", "每天一個起點（重疊）"),
            ("c T2 用日低最小值", fx_c, "close", "用收盤"),
            ("d M2 只含起點以前", fx_d, "full", "全期分位（看未來）"),
            ("f Clopper-Pearson 精確區間（補檢）", None, "wald", "常態近似（Wald）"))


def fx_f(mut=None):
    """f. CP：x＝n ⇒ 上界 1、下界＝(α/2)^(1/n)；x＝0 ⇒ 下界 0、上界＝1−(α/2)^(1/n)；x＝5、n＝10、α＝0.05 ⇒ [0.18709, 0.81291]（教科書值）。"""
    a = 0.05 / N_CELLS; ok = True
    l, u = clopper_pearson(30, 30, a, mut); ok &= abs(u - 1) < 1e-12 and abs(l - (a / 2) ** (1 / 30)) < 1e-9
    l, u = clopper_pearson(0, 30, a, mut); ok &= l == 0 and abs(u - (1 - (a / 2) ** (1 / 30))) < 1e-9
    l, u = clopper_pearson(5, 10, 0.05, mut); ok &= abs(l - 0.18709) < 1e-4 and abs(u - 0.81291) < 1e-4
    return bool(ok)


def run_fixtures():
    res = []
    for name, fx, mut, why in FIXTURES:
        fx = fx or fx_f
        g = fx(); red = not fx(mut)
        res.append({"案": name, "結果": "綠" if g else "紅", "反例": why, "反例結果": "紅（抓得到）" if red else "⛔ 仍綠"})
    return all(r["結果"] == "綠" and r["反例結果"].startswith("紅") for r in res), res


# ───────────────────────── 主計算 ─────────────────────────
def run_coin(d):
    c, low, dates = d["close"], d["low"], d["dates"]; n = len(c)
    ev = ewma_var(c)
    ma200 = pd.Series(c).rolling(200).mean().to_numpy(); ma1400 = pd.Series(c).rolling(1400).mean().to_numpy()
    rows = []
    for h in HS:
        pm = path_min_ret(c, low, h)
        for s in starts_of(n, h):
            for model in MODELS:
                b = bounds(c, low, s, h, model, pm=pm, ev=ev)
                t1, t2, t80, pmin, end = hits(c, low, s, h, b)
                rows.append({"coin": d["sym"], "h": h, "model": model, "start": dates[s], "end": dates[s + h], "P0": c[s],
                             "T1下": b[0], "T1上": b[1], "T2下": b[4], "80下": b[2], "80上": b[3], "端點收盤": end, "途中最低": pmin,
                             "T1": int(t1), "T2": int(t2), "T1_80": int(t80),
                             "MA200": ma200[s], "MA1400": ma1400[s]})
    return pd.DataFrame(rows)


def cells(R):
    out = []
    for (coin, h, model), g in R.groupby(["coin", "h", "model"], sort=False):
        g = g.sort_values("start")
        for tg in TARGETS:
            c, lo, hi, L = ci_of(g[tg].to_numpy())
            miss = g[g[tg] == 0]
            if tg == "T2":
                tail = float((miss["途中最低"] / miss["T2下"] - 1).mean()) if len(miss) else float("nan")
            else:
                mb = miss[miss["端點收盤"] < miss["T1下"]]
                tail = float((mb["端點收盤"] / mb["T1下"] - 1).mean()) if len(mb) else float("nan")
            out.append({"coin": coin, "h": h, "model": model, "target": tg, "起點數": len(g), "第一個起點": g["start"].iloc[0], "最後起點": g["start"].iloc[-1],
                        "命中數": int(g[tg].sum()), "命中率": c, "CI下": lo, "CI上": hi, "L": L,
                        "CP下": clopper_pearson(int(g[tg].sum()), len(g), 0.05 / N_CELLS)[0], "CP上": clopper_pearson(int(g[tg].sum()), len(g), 0.05 / N_CELLS)[1],
                        "原判（補檢前）": verdict(tg, lo, hi), "判定": None, "沒守住時平均跌破": tail,
                        "80%區間命中（描述）": float(g["T1_80"].mean()) if tg == "T1" else float("nan")})
    D = pd.DataFrame(out)
    D["判定"] = [verdict2(r.target, r.CI下, r.CI上, r.CP下, r.CP上) for r in D.itertuples()]
    D["補檢降級"] = [(o.startswith("判過") and not n.startswith("判過")) for o, n in zip(D["原判（補檢前）"], D["判定"])]
    return D


def ma_desc(R):
    out = []
    for (coin, h), g in R[R.model == "M1"].groupby(["coin", "h"], sort=False):
        for ma in ("MA200", "MA1400"):
            v = g[g[ma].notna()]
            above = v[v["P0"] > v[ma]]
            out.append({"coin": coin, "h": h, "均線": "200 日線" if ma == "MA200" else "200 週線（1,400 日）", "可算起點": len(v),
                        "起點已在均線下的比例": float((v["P0"] <= v[ma]).mean()) if len(v) else float("nan"),
                        "均線上的起點": len(above), "h天內跌破比例": float((above["途中最低"] < above[ma]).mean()) if len(above) else float("nan")})
    return pd.DataFrame(out)


def yearly(R):
    R = R.copy(); R["年"] = R["start"].str[:4]
    g = R.groupby(["coin", "h", "model", "年"])[["T1", "T2"]].agg(["mean", "count"])
    g.columns = [f"{a}_{b}" for a, b in g.columns]
    return g.reset_index()


def events(R):
    out = []
    for name, (a, b) in EVENTS.items():
        g = R[(R.h == 30) & (R.start < a) & (R.end >= a)]          # 區間涵蓋事件第一天
        for _, r in g.iterrows():
            out.append({"事件": name, **{k: r[k] for k in ("coin", "model", "start", "end", "P0", "T1下", "T1上", "T2下", "端點收盤", "途中最低", "T1", "T2")}})
    return pd.DataFrame(out)


# ───────────────────────── --check 參考實作 ─────────────────────────
def ref_hit(c, low, s, h, model):
    """逐列純迴圈，另寫一次。"""
    p0 = c[s]
    if model == "M1":
        rs = [math.log(c[t] / c[t - 1]) for t in range(s - 89, s + 1)]
        mu = sum(rs) / len(rs); sg = math.sqrt(sum((x - mu) ** 2 for x in rs) / (len(rs) - 1))
        lo1, hi1, lo2 = p0 * math.exp(-Z90 * sg * math.sqrt(h)), p0 * math.exp(Z90 * sg * math.sqrt(h)), p0 * math.exp(-Z90 * sg * math.sqrt(h))
    elif model == "M3":
        rs = [math.log(c[t] / c[t - 1]) for t in range(1, s + 1)]
        v0 = sum(x * x for x in rs[:30]) / 30; v = v0
        for k, x in enumerate(rs, start=1):
            v = LAM * v + (1 - LAM) * x * x if k > 30 else v0
        sg = math.sqrt(v)
        lo1, hi1, lo2 = p0 * math.exp(-Z90 * sg * math.sqrt(h)), p0 * math.exp(Z90 * sg * math.sqrt(h)), p0 * math.exp(-Z90 * sg * math.sqrt(h))
    else:
        H = [math.log(c[t + h] / c[t]) for t in range(0, s - h + 1)]
        P = [min(low[t + 1:t + h + 1]) / c[t] - 1 for t in range(0, s - h + 1)]
        q = lambda a, p: float(np.percentile(np.array(a), p))
        lo1, hi1, lo2 = p0 * math.exp(q(H, 5)), p0 * math.exp(q(H, 95)), p0 * (1 + q(P, 5))
    end = c[s + h]; pmin = min(low[s + 1:s + h + 1])
    return int(lo1 <= end <= hi1), int(pmin >= lo2)


# ───────────────────────── 網頁 ─────────────────────────
CSS = """
:root{--bg:#fbfaf7;--fg:#1d1d1b;--mut:#6b6a66;--card:#ffffff;--line:#e4e1da;--acc:#1d4ed8;--accbg:#eef3ff;--warn:#b45309;--ok:#166534}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]){--bg:#161615;--fg:#ecebe7;--mut:#a3a19b;--card:#1f1f1d;--line:#34332f;--acc:#93b4ff;--accbg:#18203a;--warn:#fbbf24;--ok:#4ade80}}
:root[data-theme="dark"]{--bg:#161615;--fg:#ecebe7;--mut:#a3a19b;--card:#1f1f1d;--line:#34332f;--acc:#93b4ff;--accbg:#18203a;--warn:#fbbf24;--ok:#4ade80}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:16px/1.65 -apple-system,"PingFang TC","Noto Sans TC","Microsoft JhengHei",sans-serif}
main{max-width:880px;margin:0 auto;padding:20px 16px 60px}h1{font-size:1.4rem;margin:.2em 0 .3em}h2{font-size:1.15rem;margin:1.8em 0 .5em;border-top:1px solid var(--line);padding-top:1em}
h3{font-size:1rem;margin:1.1em 0 .3em}.sub{color:var(--mut);font-size:.88rem}.lead{background:var(--accbg);border-left:4px solid var(--acc);padding:12px 14px;border-radius:6px;margin:14px 0}
.lead b{color:var(--acc)}.card{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:12px 14px;margin:10px 0}
.tw{overflow-x:auto;-webkit-overflow-scrolling:touch;margin:8px 0}table{border-collapse:collapse;font-size:.84rem;min-width:100%}
th,td{border-bottom:1px solid var(--line);padding:6px 8px;text-align:right;white-space:nowrap}th:first-child,td:first-child{text-align:left}
th{color:var(--mut);font-weight:600}.narrow{color:var(--warn);font-weight:600}.pass{color:var(--ok);font-weight:600}ul{padding-left:1.2em}li{margin:.25em 0}.small{font-size:.84rem;color:var(--mut)}
summary{cursor:pointer;margin:8px 0}
"""


def pct(x, nd=0):
    return "—" if x is None or (isinstance(x, float) and math.isnan(x)) else f"{x * 100:.{nd}f}%"


def build_html(meta, Cc, MA, EV, Y, fx, chk):
    e = html.escape
    h = [f"<!doctype html><html lang='zh-Hant'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>價格區間預測校準</title><style>{CSS}</style></head><body><main>"]
    h.append("<h1>價格區間預測：區間大小準不準</h1>")
    h.append(f"<div class='sub'>PREREGC12 v1（N＝108，T1、T2 都判）｜回測線｜資料 main {SHA[:10]} 現貨日 K｜窗尾 {W_END}｜讀法寫死 {FROZEN}｜產出 {e(meta['產出時間'])}</div>")
    h.append("<div class='lead'><b>結論（只談區間大小準不準）</b><ul>" + "".join(f"<li>{x}</li>" for x in meta["結論行"]) + "</ul>"
             "<div class='small'>⛔ 這不是漲跌方向的預測，也不表示哪個價位是底；「判過」只代表在 ±10pp 容忍帶內分不出偏差，不是區間保證準。</div></div>")
    h.append("<div class='card'><b>怎麼測</b>：每個起點只用當天收盤以前的資料畫未來 h 天的區間（漂移設 0），之後對答案。"
             "<br><b>T1</b>：第 h 天收盤落在中央 90% 區間內的比例（名目 90%）。<b>T2</b>：h 天內每天的最低價都沒跌破單邊 95% 下緣的比例（名目 95%）；M1／M3 的下緣是端點分布的下緣，用在途中最低上依構造偏窄，故意保留。"
             "<br>CI：stationary block bootstrap 2,000 次、信賴水準 1−0.05/108。判過＝bootstrap CI 與 Clopper-Pearson 精確區間（同信賴水準）<b>都</b>整條在容忍帶（T1 80～100%、T2 85～100%）（裁定 seq293 補檢，只降不升）；偏窄＝bootstrap CI 上界低於名目；偏寬＝bootstrap CI 下界高於名目。</div>")
    dg = Cc[Cc["補檢降級"]]
    h.append(f"<div class='card'><b>補檢（seq293）</b>：補檢前判過 {int(Cc['原判（補檢前）'].str.startswith('判過').sum())} 格，加上 Clopper-Pearson 條件後降級 {len(dg)} 格："
             + ("；".join(f"{r.coin} {r.target}・{MODEL_ZH[r.model]}・h{r.h}（{int(r.命中數)}／{int(r.起點數)}，CP［{pct(r.CP下)}～{pct(r.CP上)}］）⇒ {e(r.判定)}" for r in dg.itertuples()) or "無")
             + "。</div>")
    for tg in TARGETS:
        h.append(f"<h2>{'一' if tg == 'T1' else '二'}、{tg}：{'第 h 天收盤落在 90% 區間' if tg == 'T1' else 'h 天內最低價守住 95% 下緣'}</h2>")
        h.append("<div class='small'>每格：命中數／起點數＝命中率；boot＝block bootstrap CI；CP＝Clopper-Pearson 精確區間；判定（補檢後）。</div><div class='tw'><table><tr><th>幣（第一個起點）</th><th>h</th>" + "".join(f"<th>{MODEL_ZH[m]}</th>" for m in MODELS) + "</tr>")
        for s in COINS:
            for hh in HS:
                g = Cc[(Cc.coin == s) & (Cc.h == hh) & (Cc.target == tg)]
                cells_ = []
                for m in MODELS:
                    r = g[g.model == m].iloc[0]
                    cls = "narrow" if r["判定"] == "偏窄" else ("pass" if r["判定"].startswith("判過") else "")
                    dn = "（補檢降級）" if r["補檢降級"] else ""
                    cells_.append(f"<td>{int(r['命中數'])}／{int(r['起點數'])}＝{pct(r['命中率'])}<br>boot［{pct(r['CI下'])}～{pct(r['CI上'])}］<br>CP［{pct(r['CP下'])}～{pct(r['CP上'])}］<br><span class='{cls}'>{e(r['判定'])}{dn}</span></td>")
                r0 = g.iloc[0]
                h.append(f"<tr><td>{s}（{r0['第一個起點']}）</td><td>{hh}（{int(r0['起點數'])}）</td>" + "".join(cells_) + "</tr>")
        h.append("</table></div>")
    # 判定彙總
    h.append("<h2>三、判定彙總</h2><div class='tw'><table><tr><th>目標</th><th>模型</th><th>判過</th><th>偏窄</th><th>偏寬</th><th>測不出</th></tr>")
    for tg in TARGETS:
        for m in MODELS:
            g = Cc[(Cc.target == tg) & (Cc.model == m)]
            k = lambda p: int(g["判定"].str.startswith(p).sum())
            h.append(f"<tr><td>{tg}</td><td>{MODEL_ZH[m]}</td><td>{k('判過')}</td><td>{k('偏窄')}</td><td>{k('偏寬')}</td><td>{k('測不出')}</td></tr>")
    h.append("</table></div>")
    # 描述
    h.append("<h2>四、描述（不判）</h2><h3>80% 中央區間（T1 另一個名目）</h3><div class='tw'><table><tr><th>幣</th><th>h</th>" + "".join(f"<th>{MODEL_ZH[m]}</th>" for m in MODELS) + "</tr>")
    for s in COINS:
        for hh in HS:
            g = Cc[(Cc.coin == s) & (Cc.h == hh) & (Cc.target == "T1")]
            h.append(f"<tr><td>{s}</td><td>{hh}</td>" + "".join(f"<td>{pct(g[g.model == m]['80%區間命中（描述）'].iloc[0])}</td>" for m in MODELS) + "</tr>")
    h.append("</table></div>")
    h.append("<h3>沒守住時平均跌破多少（T2）</h3><div class='tw'><table><tr><th>幣</th><th>h</th>" + "".join(f"<th>{MODEL_ZH[m]}</th>" for m in MODELS) + "</tr>")
    for s in COINS:
        for hh in HS:
            g = Cc[(Cc.coin == s) & (Cc.h == hh) & (Cc.target == "T2")]
            h.append(f"<tr><td>{s}</td><td>{hh}</td>" + "".join(f"<td>{pct(g[g.model == m]['沒守住時平均跌破'].iloc[0], 1)}</td>" for m in MODELS) + "</tr>")
    h.append("</table></div><div class='small'>＝沒守住的起點中，途中最低 ÷ 下緣 − 1 的平均。</div>")
    h.append("<h3>200 日線、200 週線當「下緣」（使用者提問；已知不是底，只描述）</h3><div class='small'>只算起點收盤在均線之上的起點：h 天內日低跌破均線的比例。括號＝起點已經在均線之下的比例（這些不算）。</div>")
    h.append("<div class='tw'><table><tr><th>幣</th><th>均線</th>" + "".join(f"<th>h{hh}</th>" for hh in HS) + "</tr>")
    for s in COINS:
        for ma in ("200 日線", "200 週線（1,400 日）"):
            g = MA[(MA.coin == s) & (MA["均線"] == ma)]
            h.append(f"<tr><td>{s}</td><td>{ma}</td>" + "".join(f"<td>{pct(g[g.h == hh]['h天內跌破比例'].iloc[0])}（{pct(g[g.h == hh]['起點已在均線下的比例'].iloc[0])}）</td>" for hh in HS) + "</tr>")
    h.append("</table></div>")
    h.append("<h3>大事件前後（h＝30，區間涵蓋事件日的起點）</h3><div class='tw'><table><tr><th>事件</th><th>幣</th><th>模型</th><th>起點</th><th>T2 下緣</th><th>途中最低</th><th>T1 區間</th><th>端點</th></tr>")
    for _, r in EV.iterrows():
        h.append(f"<tr><td>{e(r['事件'])}</td><td>{r['coin']}</td><td>{r['model']}</td><td>{r['start']}</td><td>{r['T2下']:.4g}</td><td class='{'narrow' if not r['T2'] else ''}'>{r['途中最低']:.4g}</td>"
                 f"<td>{r['T1下']:.4g}～{r['T1上']:.4g}</td><td class='{'narrow' if not r['T1'] else ''}'>{r['端點收盤']:.4g}</td></tr>")
    h.append("</table></div><div class='small'>橘字＝沒守住／落在區間外。逐年命中率見 yearly.csv。</div>")
    h.append("<h2>五、先驗對答</h2><div class='card'><ul>" + "".join(f"<li>{e(x)}</li>" for x in meta["先驗對答"]) + "</ul></div>")
    h.append("<h2>六、驗證</h2><div class='tw'><table><tr><th>fixture</th><th>結果</th><th>反例</th><th>反例結果</th></tr>")
    for r in fx:
        h.append(f"<tr><td style='white-space:normal'>{e(r['案'])}</td><td>{r['結果']}</td><td style='white-space:normal'>{e(r['反例'])}</td><td>{e(r['反例結果'])}</td></tr>")
    h.append(f"</table></div><div class='small'>抽樣逐列重算：{chk.get('一致數', '—')}／{chk.get('抽樣數', '—')} 個起點的 T1、T2 命中一致；鏡像與副本：{e(str(chk.get('鏡像比對', '—')))}。</div>")
    h.append("<h2>七、讀的時候要注意</h2><ul><li>各幣窗起點不同（BTC 2015 起有起點，SOL 2022-08 起），起點數少的格 CI 很寬，只能判出偏窄／偏寬或測不出。</li>"
             + "".join(f"<li>{r.coin} {r.target}・{MODEL_ZH[r.model]}・h{r.h}：命中序列全是 {'1' if r['命中率'] == 1 else '0'}（{int(r['起點數'])} 個起點）⇒ bootstrap CI 退化成一個點；Clopper-Pearson 為［{pct(r['CP下'])}～{pct(r['CP上'])}］，補檢後判「{e(r['判定'])}」。起點太少，不代表區間夠寬。</li>"
                       for _, r in Cc[Cc['CI下'] == Cc['CI上']].iterrows()) +
             "<li>T2 用現貨日低；永續合約插針可能更深 ⇒ 對合約強平而言 T2 偏樂觀。</li>"
             "<li>CI 信賴水準極高（1−0.05/108），2,000 次 bootstrap 下兩端近似最小／最大值。</li>"
             "<li>⛔ 不得把區間當成「幣價會在 A～B 之間」對外講、⛔ 不得用下緣推開幾倍、⛔ 不構成買賣建議。前瞻紀錄另記（24 筆前不下結論）。</li></ul>")
    h.append("<h2>八、執行者補的讀法</h2><ul class='small'>" + "".join(f"<li>{e(x)}</li>" for x in meta["執行者補"]) + "</ul></main></body></html>")
    return "\n".join(h)


EXEC_SUPPLIED = [
    "Q3 M1 標準差用樣本標準差（ddof＝1）",
    "Q4 M3 EWMA 初值＝前 30 個日報酬平方的平均（730 天暖機後影響可忽略）",
    "Q5 M2 用重疊的 h 天窗取樣（t＋h ≤ 起點）；途中最低跌幅用 t＋1～t＋h 的日低",
    "Q6 「起點後 h 天內」＝起點隔天起的 h 根日 K（起點當天日低不算）",
    "Q7 命中序列全 1／全 0 時 CI＝點估計；百分位用 numpy 線性內插",
    "Q8 在容忍帶內又同時上界＜名目（或下界＞名目）時，依登錄順序判「判過」，另註略窄／略寬",
    "Q9 均線當下緣只算起點收盤在均線之上的起點；起點已在均線下的比例另報",
    "Q10 先驗①「多數」＝36 格中過半；②＝≥4 幣；④「遠高於 5%」＝每個 h 合併跌破比例 ≥15%",
    "Q12（補檢 seq293）被降級的格：偏窄／偏寬要 bootstrap 與 Clopper-Pearson 兩者同向才給，否則測不出",
]


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--check", action="store_true"); a = ap.parse_args()
    t0 = time.time()
    ok, fx = run_fixtures()
    for r in fx:
        print(f"[fixture {r['案']}] {r['結果']}｜反例「{r['反例']}」⇒ {r['反例結果']}")
    assert ok, "⛔ fixture 沒全過，停"
    os.makedirs(OUT, exist_ok=True)
    data = {s: load(s) for s in COINS}
    for s in COINS:
        d = data[s]; print(f"[{s}] {d['dates'][0]}～{d['dates'][-1]}（{len(d['dates'])} 天）｜第一個起點 {d['dates'][WARM]}｜起點數 " + "／".join(str(len(starts_of(len(d['close']), hh))) for hh in HS))
    if a.check:
        mir = {}
        for s in COINS:
            f1, f2 = os.path.join(ROOT, f"{s}.csv"), os.path.join(MIRROR, f"{s}.csv")
            mir[s] = "相同" if os.path.exists(f2) and hashlib.sha256(open(f1, "rb").read()).hexdigest() == hashlib.sha256(open(f2, "rb").read()).hexdigest() else "不同"
        R = pd.concat([run_coin(data[s]) for s in COINS], ignore_index=True)
        rng = np.random.default_rng(SEED); idx = rng.choice(len(R), 30, replace=False); rows = []
        for i in idx:
            r = R.iloc[int(i)]; d = data[r.coin]; s = int(np.flatnonzero(d["dates"] == r.start)[0])
            t1, t2 = ref_hit(d["close"], d["low"], s, int(r.h), r.model)
            rows.append({"coin": r.coin, "h": int(r.h), "model": r.model, "start": r.start, "參考T1": t1, "引擎T1": int(r.T1), "參考T2": t2, "引擎T2": int(r.T2), "一致": bool(t1 == r.T1 and t2 == r.T2)})
        chk = {"讀法寫死": FROZEN, "fixture全過": ok, "fixture": fx, "鏡像比對": "6 檔全相同" if all(v == "相同" for v in mir.values()) else mir,
               "抽樣數": len(rows), "一致數": int(sum(x["一致"] for x in rows)), "抽樣": rows, "種子": SEED}
        json.dump(chk, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
        print(f"[check] 鏡像 {chk['鏡像比對']}｜抽樣 {chk['一致數']}／{chk['抽樣數']} 一致")
        assert chk["一致數"] == chk["抽樣數"], "⛔ 抽樣重算不一致"
        return
    R = pd.concat([run_coin(data[s]) for s in COINS], ignore_index=True)
    R.to_csv(os.path.join(OUT, "starts.csv"), index=False)
    Cc = cells(R); Cc.to_csv(os.path.join(OUT, "cells.csv"), index=False)
    MA = ma_desc(R); MA.to_csv(os.path.join(OUT, "ma_desc.csv"), index=False)
    Y = yearly(R); Y.to_csv(os.path.join(OUT, "yearly.csv"), index=False)
    EV = events(R); EV.to_csv(os.path.join(OUT, "events.csv"), index=False)
    # 先驗
    pri = []
    g1 = Cc[(Cc.target == "T2") & Cc.model.isin(["M1", "M3"])]; n1 = int((g1["判定"] == "偏窄").sum())
    pri.append(f"① T2 用 M1／M3 端點下緣多數格偏窄：{n1}／{len(g1)} 格偏窄 ⇒ " + ("中" if n1 > len(g1) / 2 else "未中"))
    g2 = Cc[(Cc.target == "T1") & (Cc.h == 7)]; closer = []
    for s in COINS:
        c1 = g2[(g2.coin == s) & (g2.model == "M1")]["命中率"].iloc[0]; c3 = g2[(g2.coin == s) & (g2.model == "M3")]["命中率"].iloc[0]
        if abs(c3 - 0.9) < abs(c1 - 0.9):
            closer.append(s)
    pri.append(f"② T1 h7 M3 比 M1 更接近 90%：{len(closer)}／6 幣（{'、'.join(closer) or '無'}）⇒ " + ("中" if len(closer) >= 4 else "未中"))
    g3 = Cc[(Cc.target == "T1") & (Cc.h == 30) & (Cc.model == "M2")]; nar = list(g3[g3["判定"] == "偏窄"].coin)
    pri.append(f"③ 至少一幣 T1 h30 M2 偏窄：{len(nar)} 幣（{'、'.join(nar) or '無'}）⇒ " + ("中" if nar else "未中"))
    pooled = {}
    for hh in HS:
        g = R[(R.model == "M1") & (R.h == hh) & R.MA200.notna() & (R.P0 > R.MA200)]
        pooled[hh] = float((g["途中最低"] < g["MA200"]).mean())
    pri.append("④ 200 日線當下緣，途中跌破比例遠高於 5%：6 幣合併 " + "、".join(f"h{k} {pct(v, 1)}" for k, v in pooled.items()) + " ⇒ " + ("中" if all(v >= 0.15 for v in pooled.values()) else "未中"))
    lines = []
    for tg in TARGETS:
        for m in MODELS:
            g = Cc[(Cc.target == tg) & (Cc.model == m)]
            k = lambda p: int(g["判定"].str.startswith(p).sum())
            lines.append(f"<b>{tg}・{MODEL_ZH[m]}</b>：18 格中 判過 {k('判過')}、偏窄 {k('偏窄')}、偏寬 {k('偏寬')}、測不出 {k('測不出')}；命中率範圍 {pct(g['命中率'].min())}～{pct(g['命中率'].max())}（名目 {pct(NOM[tg])}）。")
    meta = {"登錄": "PREREGC12 價格區間預測校準 v1 sha84310aa20866d282", "裁定": "seq292（N＝108）", "讀法寫死": FROZEN, "資料commit": SHA,
            "產出時間": pd.Timestamp.now(tz="Asia/Taipei").strftime("%Y-%m-%d %H:%M（台北）"),
            "各幣窗": {s: [data[s]["dates"][0], data[s]["dates"][-1], data[s]["dates"][WARM], {hh: int(len(starts_of(len(data[s]["close"]), hh))) for hh in HS}] for s in COINS},
            "結論行": lines, "先驗對答": pri, "200日線合併跌破": pooled, "fixture": fx, "執行者補": EXEC_SUPPLIED, "耗時秒": round(time.time() - t0, 1),
            "補檢": {"時間": "2026-10-04 18:40（台北）", "依據": "seq293 §一", "補檢前判過": int(Cc["原判（補檢前）"].str.startswith("判過").sum()),
                     "降級": [f"{r['coin']} {r['target']} {r['model']} h{r['h']}：{r['原判（補檢前）']} ⇒ {r['判定']}（{int(r['命中數'])}／{int(r['起點數'])}，CP {r['CP下']:.4f}～{r['CP上']:.4f}）"
                              for _, r in Cc[Cc["補檢降級"]].iterrows()]}}
    json.dump(meta, open(os.path.join(OUT, "meta.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    cp = os.path.join(OUT, "check.json"); chk = json.load(open(cp, encoding="utf-8")) if os.path.exists(cp) else {}
    open(os.path.join(OUT, "價格區間預測校準.html"), "w", encoding="utf-8").write(build_html(meta, Cc, MA, EV, Y, fx, chk))
    import re
    for x in lines + pri:
        print(re.sub(r"<[^>]+>", "", x))
    print(f"完成 {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()

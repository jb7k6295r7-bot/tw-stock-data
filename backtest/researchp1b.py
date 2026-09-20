"""PREREGP1b（seq=4 全文 sha `030037766eeff4c6` ＋ seq=5 補件 sha `6f29b8d9730becf5`）：**尺能不能變細**。

    python3 -m backtest.researchp1b [--out backtest/resultsp1b]

⭐ 主要輸出 ＝【每一格的假訊號組 95% CI 半寬】（⛔ 不是超額、不是勝率、不是 lift）。
⛔ 判定格依 seq=5 差異三 ＝ H{60,120} × rule{null,relvol} × d=∞ × N{3,5,8,10,20,30,40}
   ＝ **4 組 × 7 格，四組都要通過**；⛔ 任一組沒過就判沒通過、⛔ 不可挑、⛔ 不可平均（〈一百〇八〉）。

⛔⛔ 「同一支程式」這件事**不能用嘴講**：產生 AND 那 44 列的腳本當時沒有 commit。
⇒ ⭐ 本檔用【可證的等價】兩道閘門（登錄 §9-2），⛔ 缺一不可：
   ① `placebo_halfwidth_4C.csv` 的內容 sha256 ＝ 依賴 1 釘死的值
   ② 用本檔的實作重算 AND 44 列 ⇒ 與該檔【逐位元相同】（float repr 逐字比）
   ⛔ 任一道沒過 ⇒ 停跑回報，⛔ 不改判準、⛔ 不放寬容差。

⚠ 種子那一格【兩個都跑、⛔ 本線不挑】（登錄 §9-4）：
   (甲) 20260915（＝AND 那一側）　(乙) 20261915 ＝ 20260915+1000（＝登錄 §四 字面）
   ⇒ ✅ 判定要兩個種子都通過；⚠ 兩者判定不同 ⇒ ⛔ 停下來回報。
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import os

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
P1 = os.path.join(HERE, "resultsp1")
RESULTS = os.path.join(HERE, "resultsp1b")
AND_TABLE = os.path.join(P1, "placebo_halfwidth_4C.csv")
AND_SHA = "fe16691c6b3950d864c3682c4ad0fc8076b27768b01be6f2f4d4b9b58faa51be"   # 依賴 1（〈七十九〉）
PERM_ITER = 200                  # ⛔ 停排條件逐字禁止改重抽次數
PERM_SEEDS = (20260915, 20261915)   # (甲) AND 那一側／(乙) 登錄 §四 字面 20260915+1000
PCT = (2.5, 97.5)
COST_PP = 0.585                  # 〈四十九〉第四條的參照（單筆來回成本）
HS = (60, 120)
RULES = ("null", "relvol")
JUDGE_NS = (3, 5, 8, 10, 20, 30, 40)
MIN_N = 24                       # 出口ⓐ
MIN_CELLS = 5                    # 出口ⓑ
BLK_REASONS = ("a", "b", "b_expired")   # ⛔ 排除 "c"
P1_SEED0, P1_REPS = 7000, 200    # PREREGP1 模擬種子區間（不重疊斷言用）


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def two_groups(df: pd.DataFrame, H: int):
    """一格的兩組：進場組 ＝ reason=="in"；假訊號組 ＝ reason ∈ {a,b,b_expired}（⛔ 排除 c）。

    ⚠ 逐 H 各自 dropna ⇒ n_in／n_blk 在 H60 與 H120 不同（AND 那份檔就是這樣）。
    """
    col = f"g_H{H}"
    ent = df[df["reason"] == "in"][col].dropna().to_numpy(float)
    blk = df[df["reason"].isin(BLK_REASONS)][col].dropna().to_numpy(float)
    return ent, blk


def halfwidth(ent: np.ndarray, blk: np.ndarray, seed: int, n_iter: int = PERM_ITER) -> dict:
    """標籤重排 n_iter 次 ⇒ 95% 帶與半寬（⭐ 本件唯一的一份實作，AND 與 S 都走它）。"""
    n = len(ent)
    out = {"n_in": n, "n_blk": len(blk), "diff_pp": np.nan, "hw95_pp": np.nan,
           "band_lo": np.nan, "band_hi": np.nan}
    if n == 0 or len(blk) == 0:
        return out
    out["diff_pp"] = (ent.mean() - blk.mean()) * 100
    pool = np.concatenate([ent, blk])
    rng = np.random.default_rng(seed)          # ⭐ 每一格各自重新建（AND 那份就是這樣）
    d = np.empty(n_iter)
    for i in range(n_iter):
        p = rng.permutation(pool)
        d[i] = (p[:n].mean() - p[n:].mean()) * 100
    lo, hi = np.percentile(d, PCT)
    out.update(band_lo=float(lo), band_hi=float(hi), hw95_pp=float((hi - lo) / 2))
    return out


def _cellkey(path: str):
    """檔名 → (N, d, rule)。⚠ N 留成字串排序（AND 那份檔的列序就是檔名排序）。"""
    stem = os.path.basename(path).split(".")[0].split("_")
    return stem[2][1:], stem[3][1:], stem[4]


def table(set_name: str, seed: int, src: str = P1) -> pd.DataFrame:
    """一個訊號集的 44 列（22 格 × 2 個 H），列序 ＝ glob 排序 × H。"""
    rows = []
    for f in sorted(glob.glob(os.path.join(src, f"blocked_{set_name}_*.csv.gz"))):
        N, d, rule = _cellkey(f)
        df = pd.read_csv(f)
        for H in HS:
            ent, blk = two_groups(df, H)
            r = {"N": N, "d": d, "rule": rule, "H": H, **halfwidth(ent, blk, seed)}
            r["reading"] = "量不準（hw>0.585）" if not (r["hw95_pp"] <= COST_PP) else "可判"
            rows.append(r)
    return pd.DataFrame(rows)


LABELS = ("N", "d", "rule", "H")
NUMS = ("n_in", "n_blk", "diff_pp", "hw95_pp", "band_lo", "band_hi")


def read_table(path: str) -> pd.DataFrame:
    """讀半寬表。⛔⛔ 一定要 `keep_default_na=False`：

    ⚠ pandas 的預設缺值清單含字串 **"null"** ⇒ rule 欄的 `null` 會被讀成 **NaN**，
      而那正是本件的兩個 rule 之一 ⇒ ⛔ 整組 null 的格會靜靜對不上（⭐ 自測有一條專門擋它）。
    ⚠ 同理 d 欄的 `inf` 會被讀成 float inf ⇒ 標籤一律當字串讀。
    """
    return pd.read_csv(path, comment="#", keep_default_na=False,
                       dtype={"N": str, "d": str, "rule": str, "reading": str})


def same_as_file(got: pd.DataFrame, path: str) -> tuple[bool, list]:
    """閘門二：與釘死的那份檔【逐位元相同】（float 用 repr 逐字比，⛔ 不設容差）。"""
    want = read_table(path)
    bad = []
    if len(got) != len(want):
        return False, [f"列數 {len(got)} vs {len(want)}"]
    for i in range(len(want)):
        a, b = got.iloc[i], want.iloc[i]
        for c in LABELS:
            if str(a[c]) != str(b[c]):
                bad.append(f"第 {i} 列 {c}：{a[c]} vs {b[c]}")
        for c in NUMS:
            if repr(float(a[c])) != repr(float(b[c])):
                bad.append(f"第 {i} 列 {c}：{a[c]!r} vs {b[c]!r}")
    return not bad, bad


def judged(tab: pd.DataFrame, H: int, rule: str) -> pd.DataFrame:
    """一組（H×rule）的 7 個判定格，⛔ 照 JUDGE_NS 的順序、d=∞。"""
    t = tab[(tab["H"] == H) & (tab["rule"] == rule) & (tab["d"] == "inf")].copy()
    t["N"] = t["N"].astype(int)
    t = t[t["N"].isin(JUDGE_NS)].sort_values("N").reset_index(drop=True)
    return t


def judge_group(s: pd.DataFrame, a: pd.DataFrame) -> dict:
    """一組的 H1／H2（⭐ 出口ⓐ 先剔格、ⓑ 再看格數）。"""
    m = s.merge(a, on="N", suffixes=("_s", "_a"))
    m["n_s"] = m["n_in_s"] + m["n_blk_s"]
    m["n_a"] = m["n_in_a"] + m["n_blk_a"]
    drop = m[(m["n_s"] < MIN_N) | (m["n_a"] < MIN_N)]
    m = m[(m["n_s"] >= MIN_N) & (m["n_a"] >= MIN_N)].copy()
    m["pair"] = m["hw95_pp_s"] - m["hw95_pp_a"]
    cells = int(len(m))
    if cells < MIN_CELLS:
        return {"cells": cells, "dropped": int(len(drop)), "h1": "還沒測", "h2": "還沒測", "tab": m}
    win = int((m["pair"] < 0).sum())
    med = float(m["pair"].median())
    h1 = "通過" if (win >= MIN_CELLS and med < 0) else "沒通過"
    fine = int((m["hw95_pp_s"] <= COST_PP).sum())
    return {"cells": cells, "dropped": int(len(drop)), "win": win, "med": med, "mean": float(m["pair"].mean()),
            "sd": float(m["pair"].std(ddof=1)), "nonzero": int((m["pair"] != 0).sum()),
            "fine": fine, "h1": h1, "h2": "通過" if fine >= 1 else "沒通過", "tab": m}


def h3_fit(tab: pd.DataFrame) -> dict:
    """H3（診斷）：hw95 ~ 1/√n 的斜率與 R²。⛔ 不佔判定格。"""
    t = tab.dropna(subset=["hw95_pp"]).copy()
    t["n"] = t["n_in"] + t["n_blk"]
    x = 1 / np.sqrt(t["n"].to_numpy(float)); y = t["hw95_pp"].to_numpy(float)
    if len(x) < 3:
        return {"n_cells": int(len(x)), "slope": np.nan, "intercept": np.nan, "r2": np.nan}
    b, a0 = np.polyfit(x, y, 1)
    yh = a0 + b * x
    ss = float(((y - y.mean()) ** 2).sum())
    return {"n_cells": int(len(x)), "slope": float(b), "intercept": float(a0),
            "r2": float(1 - ((y - yh) ** 2).sum() / ss) if ss > 0 else np.nan}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=RESULTS)
    ap.add_argument("--src", default=P1)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    log = lambda s: print(s, flush=True)

    # ── 閘門一：依賴 1 的 sha256 ──
    got_sha = sha256_file(AND_TABLE)
    if got_sha != AND_SHA:
        raise SystemExit(f"⛔ 依賴 1 的 sha256 對不上 ⇒ 停跑\n  want {AND_SHA}\n  got  {got_sha}")
    log(f"[閘門一] ✅ placebo_halfwidth_4C.csv sha256 ＝ 釘死的值")

    # ── 閘門二：用本檔的實作重算 AND，逐位元比 ──
    and_re = table("AND", PERM_SEEDS[0], a.src)
    ok, bad = same_as_file(and_re, AND_TABLE)
    and_re.to_csv(os.path.join(a.out, "and_recompute.csv"), index=False)
    if not ok:
        open(os.path.join(a.out, "P1b_STOP.md"), "w", encoding="utf-8").write(
            "# PREREGP1b：⛔ 停跑（閘門二 —— 重算 AND 對不上）\n\n" + "\n".join(f"- {x}" for x in bad[:40]) + "\n")
        raise SystemExit(f"⛔ 閘門二沒過：重算 AND 與釘死的檔有 {len(bad)} 處不同 ⇒ 停跑（已寫 P1b_STOP.md）")
    log(f"[閘門二] ✅ 重算 AND 的 {len(and_re)} 列與釘死的檔【逐位元相同】⇒ 本檔的實作與當時那支不可分辨")

    # ── S 的兩個種子 ──
    tabs = {s: table("S", s, a.src) for s in PERM_SEEDS}
    for s, t in tabs.items():
        t.to_csv(os.path.join(a.out, f"s_halfwidth_seed{s}.csv"), index=False)

    port = pd.read_csv(os.path.join(a.src, "portfolio.csv"))
    port["rule"] = port["rule"].fillna("null")

    L = [f"# PREREGP1b：S 集合能不能讓尺變細 —— 結果",
         "",
         "⛔ **第一段就要寫的那一句（§五①）**：本件**不回答** PREREGP1 的原問題（上限的成本是多少）。",
         "⛔ 本件只量【尺的粗細】：每一格假訊號組 95% CI 的半寬。⛔ 不報超額、勝率、lift。", "",
         "## 〇、⭐ 計算式（＝依賴 1③ 要的那一段，⛔ 首行就貼）", "",
         "```",
         f"資料　　每格的代表種子 log（resultsp1/blocked_{{SET}}_N*_d*_*.csv.gz；⚠ 檔名叫 blocked 但它是整份 log）",
         '兩組　　進場組 ＝ reason=="in"；假訊號組 ＝ reason ∈ {"a","b","b_expired"}（⛔ 排除 "c"）',
         "　　　　逐 H 各自 dropna(g_H{H}) ⇒ n_in／n_blk 逐 H 不同",
         "統計量　diff_pp ＝ (進場組平均 − 假訊號組平均) × 100",
         f"重排　　pool ＝ concat(兩組)；rng ＝ np.random.default_rng(PERM_SEED)【每一格各自重新建】",
         f"　　　　重複 {PERM_ITER} 次：p ＝ rng.permutation(pool)；d_i ＝ (p[:n_in].mean() − p[n_in:].mean()) × 100",
         f"帶　　　band ＝ np.percentile(d, {list(PCT)})（numpy 預設 linear 內插）；hw95 ＝ (hi − lo) / 2",
         f"種子　　seed_0 ＝ {PERM_SEEDS[0]}／{PERM_SEEDS[1]}，R ＝ {PERM_ITER}（重排次數）",
         f"　　　　⭐ 與 PREREGP1 的模擬種子區間 [{P1_SEED0}, {P1_SEED0 + P1_REPS - 1}] **不重疊**",
         f"　　　　⚠ (甲) {PERM_SEEDS[0]} 與 P1b 第一版的 seed_0 相同 —— ⭐ 刻意的：那是 AND 基準那一側的種子，",
         "　　　　　 ⛔ 不是本件的模擬種子（本件不跑模擬，只重排已存在的 log）",
         f"環境　　pandas {pd.__version__}／numpy {np.__version__}",
         "```", "",
         "## 一、⛔⛔ 兩道閘門（⭐「同一支程式」是**證**出來的，⛔ 不是講出來的）", "",
         "```",
         "⛔ 事實：產生 AND 那 44 列的腳本【當時沒有 commit】（b795842db 只收了 csv）",
         f"閘門一 ✅ placebo_halfwidth_4C.csv 內容 sha256 ＝ {AND_SHA[:16]}…（＝依賴 1 釘死的值）",
         f"閘門二 ✅ 用本檔的實作重算 AND 的 {len(and_re)} 列 ⇒ 與該檔【逐位元相同】（float repr 逐字比、⛔ 零容差）",
         "⇒ ⭐ 兩道都過 ⇒ 本檔的實作與當時那支【在這 44 列上不可分辨】⇒ 才算 S",
         "```", ""]

    # ── 判定（兩個種子、四組） ──
    verdict = {}
    for seed in PERM_SEEDS:
        for H in HS:
            for rule in RULES:
                verdict[(seed, H, rule)] = judge_group(judged(tabs[seed], H, rule), judged(and_re, H, rule))
    L += ["## 二、⭐⭐ 判定（保守法：**四組都要通過**，⛔ 不可挑、⛔ 不可平均）", "",
          "> 原登錄 §四 未指定 **rule** 與 **H 別**，本次以保守法處理（四組都要通過）；",
          "> ⛔ 此為登錄缺陷的補救，**不是判準的選擇**。（〈一百〇八〉）", "",
          "| 種子 | 組（H×rule） | 判定格 | S 半寬較小的格數 | 配對差中位(pp) | H1 | S 半寬 ≤0.585 的格數 | H2 |",
          "|---|---|---:|---:|---:|---|---:|---|"]
    for (seed, H, rule), v in verdict.items():
        L.append(f"| {seed} | H{H}×{rule} | {v['cells']} | {v.get('win', '—')} | "
                 f"{v.get('med', float('nan')):+.3f} | **{v['h1']}** | {v.get('fine', '—')} | **{v['h2']}** |")
    h1_all = sorted({v["h1"] for v in verdict.values()})
    h2_all = sorted({v["h2"] for v in verdict.values()})
    H1 = "通過" if h1_all == ["通過"] else ("還沒測" if "還沒測" in h1_all else "沒通過")
    H2 = "通過" if h2_all == ["通過"] else ("還沒測" if "還沒測" in h2_all else "沒通過")
    split = {s: sorted({verdict[(s, H, r)]["h1"] for H in HS for r in RULES}) for s in PERM_SEEDS}
    L += ["", f"### ⇒ **H1 {H1}**／**H2 {H2}**（⭐ 8 組全部要通過才算通過：4 組 × 2 個種子）", ""]
    if split[PERM_SEEDS[0]] != split[PERM_SEEDS[1]]:
        L += ["⛔⛔ **兩個種子的判定不同 ⇒ 依登錄 §9-4 停下來回報，⛔ 本線不挑一個。**", ""]
    else:
        L += [f"✅ 兩個重排種子的判定【相同】（{'／'.join(split[PERM_SEEDS[0]])}）⇒ ⭐ 那一格的選擇在本件不影響結果。", ""]

    # ── 必報① 逐格半寬並列 ──
    L += ["## 三、必報① 逐格半寬（S 與 AND 並列，⭐ 同一張表；種子 (甲) " + str(PERM_SEEDS[0]) + "）", "",
          "| 組 | N | AND 半寬(pp) | S 半寬(pp) | 配對差 S−AND | AND n | S n |", "|---|---:|---:|---:|---:|---:|---:|"]
    for H in HS:
        for rule in RULES:
            v = verdict[(PERM_SEEDS[0], H, rule)]
            for r in v["tab"].itertuples():
                L.append(f"| H{H}×{rule} | {r.N} | {r.hw95_pp_a:.3f} | {r.hw95_pp_s:.3f} | {r.pair:+.3f} | "
                         f"{int(r.n_a)} | {int(r.n_s)} |")
    L += ["", "## 四、必報③ 配對差（S − AND）的四個數（⛔〈七十四〉：不可只報平均）", "",
          "| 種子 | 組 | 中位 | 平均 | 標準差 | 非零格數 |", "|---|---|---:|---:|---:|---:|"]
    for (seed, H, rule), v in verdict.items():
        if "med" in v:
            L.append(f"| {seed} | H{H}×{rule} | {v['med']:+.3f} | {v['mean']:+.3f} | {v['sd']:.3f} | {v['nonzero']}/{v['cells']} |")

    # ── H3 ──
    L += ["", "## 五、必報④ H3（診斷，⛔ 不佔判定格）：半寬 vs 1/√n", "",
          "| 集合 | 格數 | 斜率 | 截距 | R² |", "|---|---:|---:|---:|---:|"]
    fits = {"AND": h3_fit(and_re), "S": h3_fit(tabs[PERM_SEEDS[0]]),
            "AND＋S": h3_fit(pd.concat([and_re, tabs[PERM_SEEDS[0]]], ignore_index=True))}
    for k, f in fits.items():
        L.append(f"| {k} | {f['n_cells']} | {f['slope']:.3f} | {f['intercept']:+.3f} | {f['r2']:.3f} |")
    fit = fits["AND＋S"]
    L += [""]
    if not (np.isfinite(fit["slope"]) and fit["slope"] > 0):
        L += [f"⇒ ⚠ 合併那條的斜率 {fit['slope']:.3f} 不是正的 ⇒ ⛔ 外推無意義（⭐ 那本身就是「加樣本救不了」的證據）"]
    elif COST_PP > fit["intercept"]:
        need = (fit["slope"] / (COST_PP - fit["intercept"])) ** 2
        L += [f"⇒ ⭐ 依合併那條外推：要把半寬壓到 {COST_PP}pp，每格需要 **n ≈ {need:,.0f}**（⭐ 停排條件要用的就是這個數）"]
    else:
        L += [f"⇒ ⛔ 截距（{fit['intercept']:+.3f}pp）已經 ≥ {COST_PP}pp ⇒ **加樣本永遠到不了**（外推無解）"]
    L += ["", "⚠ §五④：半寬同時受【樣本數】與【個股報酬離散度】影響 ⇒ ⭐ H3 只能量到兩者的合成，⛔ 分不開。", ""]

    # ── ⑤⑥ ──
    L += ["## 六、必報⑤⑥ 槽位使用率與放棄組（⭐ 沿用 PREREGP1 那一趟，⛔ 本件不重跑模擬）", "",
          "| 集合 | N | rule | 槽位使用率 | m（進場次數） | deferred | expired |", "|---|---:|---|---:|---:|---:|---:|"]
    for st in ("AND", "S"):
        for N in JUDGE_NS:
            for rule in RULES:
                q = port[(port["set"] == st) & (port["N"] == N) & (port["rule"] == rule) & (port["d"] == "inf")]
                if len(q):
                    r = q.iloc[0]
                    L.append(f"| {st} | {N} | {rule} | {r['slot'] * 100:.1f}% | {r['m']:.0f} | {r['deferred']:.0f} | {r['expired']:.0f} |")
    L += ["", "## 七、⛔ 限制（逐字沿用登錄 §五）", "",
          "- ⛔ ① 本件**不回答** P1 的原問題（上限的成本是多少）。",
          "- ⛔ ② AND 與 S 巢狀（AND ＝ S ∩ 面板 rev_hi24）⇒ 半寬**不獨立** ⇒ 只可配對比較，⛔ 不可做兩組檢定。",
          "- ⛔ ③ 期間沿用 P1 ⇒ 不含 2008／2000。",
          "- ⛔ ④ 半寬同時受樣本數與個股報酬離散度影響 ⇒ H3 量到的是合成，⛔ 分不開。",
          "- ⚠ ⑤ R1 的 p70 門檻是策略線事前訂的，⛔ 沒有外部依據。",
          "- ✅ 依賴〈零之二〉那句確認：**S 的定義不用 rev_hi24**（S ＝ `results11/signals.csv.gz`）；",
          "  ⚠ 而 **AND 用**（AND ＝ S ∩ 面板 rev_hi24）⇒ ⛔ 但①型量級凍結凍的是【四型數字】不是 rev_hi24 的定義",
          "  ⇒ ✅ 本件**不受**①型量級凍結影響。",
          "- ⚠ 閘門三件（〈八十二〉）與缺值處置屬於 PREREGP1 那一趟 ⇒ 本件沿用，⛔ 不重新裁。", ""]
    p = os.path.join(a.out, "P1B_REPORT.md")
    open(p, "w", encoding="utf-8").write("\n".join(L) + "\n")
    log("\n".join(L))
    log(f"[out] {p}")


if __name__ == "__main__":
    main()

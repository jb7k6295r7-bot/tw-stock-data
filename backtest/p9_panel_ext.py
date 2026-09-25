# -*- coding: utf-8 -*-
"""PREREGP9 2-B ⓑ 用：P4 面板的量測日延伸到 2026-04～08（裁定線 seq167 §四）。回測線，2026-09-25。

    cd ~/tw-p17 && ~/tw-p16/.venv/bin/python backtest/p9_panel_ext.py [--procs 2]     # 建面板 ⇒ resultsp9_engine/panel_ext.csv.gz
    cd ~/tw-p17 && ~/tw-p16/.venv/bin/python backtest/p9_panel_ext.py --sha           # 三份 panel 的 sha256 ⇒ PANEL_SHA.md 檔尾加一節

⭐ 裁定線 seq167 §四（逐字要點）：「面板補 2026-04～08 量測日 ⇒ ✅ 補（登錄是持有中每個量測日判，不補＝靜默當『不加碼』）。
   條件：同一套 build_panel、同一 data commit；重疊處逐位元同的 fixture；補後的 panel 另記新 sha、舊 sha 並列。」

⭐ 定義一律照既有程式，⛔ 本檔不寫第二套（本檔只做「挑量測日、呼叫、遮報酬欄、寫檔」）：
  資料    researchH2（main edc6f8002f 快照；import 時 D.DATA 指到 ~/h2data/<sha>/data）＝ researchAFC_panel 同一份
  母體    universe_gate.gate3(meta/stocks.csv) ∩ data.load_universe()（＝ researchAFC_panel 同一式；⭐ gate3 全體，
          因為 2-B ⓑ 是【橫斷面】三分位，⛔ 不可只算少數股）
  面板    researchp4.build_panel（同一支；min_periods 常設斷言照開，不一致 > 0 ⇒ 停，同 researchAFC_panel）
  量測日  p4_features.measurement_days(cal, "2015-01-01", ASOF)：舊面板那一段（～2026-03-31）＋ 新增的 2026-04-01～ASOF

落地讀法（⛔ 在看任何結果之前寫定）：
 E1 ASOF ＝ 2026-08-24（＝ researchH2／rerun17 的 W1，P9 主窗終點）⇒ 新增量測日 ＝ (2026-03-31, 2026-08-24] 內的每月第一個交易日。
 E2 ⛔⛔ 新增量測日的 fwd_20／fwd_60／fwd_120（＝ 報酬）一律寫 NaN：本件只為了產 2-B ⓑ 旗標，⛔ 不讀也不存任何報酬。
    （build_panel 的工人會順手算，本檔在寫檔前、任何人看之前就蓋成 NaN；欄位仍保留 ⇒ 欄名與欄序跟舊面板完全相同。）
    舊面板那一段的 fwd_* 原樣保留（它們本來就在 git 裡的 resultsAFC/panel.csv.gz）。
 E3 輸出 ＝【舊面板檔讀回來的列】＋【新增量測日的列】，再依 (measure_date, stock_id) 排（＝ build_panel 的排序）。
    寫檔前先斷言：同一次 build_panel 重算出的舊量測日那一段 ＝ 舊面板【逐列逐欄逐位元】相同（不同 ⇒ 停、不寫檔）。
 E4 gzip 標頭的 mtime 固定為 0 ⇒ 同樣內容、同樣檔名重跑 sha256 不變（gzip 標頭另記檔名 ⇒ 換檔名 sha 就變）；舊的兩份面板是預設 mtime，sha 會隨寫檔時間變。
"""
from __future__ import annotations

import argparse
import hashlib
import os
import sys
import time

sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
import researchH2 as H2                       # noqa: E402  把 D.DATA 指到快照（並 chdir 到 ~/tw-p17）
import contextlib                             # noqa: E402
import io                                     # noqa: E402
import numpy as np                            # noqa: E402
import pandas as pd                           # noqa: E402
from backtest import data as D                # noqa: E402
from backtest import p4_features as P         # noqa: E402
from backtest import researchp4 as RP4        # noqa: E402
from backtest import universe_gate as UG      # noqa: E402

START = "2015-01-01"                          # researchAFC_panel 的量測日起點
OLD_END = "2026-03-31"                        # researchAFC_panel 的量測日終點
ASOF = "2026-08-24"                           # E1（＝ researchH2.W1）
OLD_PANEL = "backtest/resultsAFC/panel.csv.gz"
OLD_PANEL_P4 = "backtest/resultsp4/panel.csv.gz"
OUT_DIR = "backtest/resultsp9_engine"
OUT = os.path.join(OUT_DIR, "panel_ext.csv.gz")
FWD = [f"fwd_{H}" for H in RP4.HOLDS]
assert ASOF == H2.W1, "E1：ASOF 要等於 P9 主窗終點 researchH2.W1"


def load_gate3() -> pd.DataFrame:
    """gate3 ∩ load_universe（researchAFC_panel 同一式）；讀 D.DATA（⭐ 跟著指標走，selftest 會換）。"""
    stocks = pd.read_csv(os.path.join(D.DATA, "meta", "stocks.csv"), dtype=str)
    with contextlib.redirect_stdout(io.StringIO()):
        g = UG.gate3(stocks)
    return D.load_universe().merge(g[["stock_id"]], on="stock_id")


def positions(cal: pd.DatetimeIndex) -> tuple[np.ndarray, np.ndarray]:
    """(全部量測日, 新增量測日) 的日曆位置。"""
    allp = P.measurement_days(cal, START, ASOF)
    newp = allp[cal[allp] > pd.Timestamp(OLD_END)]
    return allp, newp


def mask_fwd(df: pd.DataFrame) -> pd.DataFrame:
    """E2：新增量測日的 fwd_* 蓋成 NaN（⛔ 不讀也不存報酬）。"""
    df = df.copy()
    df.loc[df["measure_date"] > pd.Timestamp(OLD_END), FWD] = np.nan
    return df


def frames_identical(a: pd.DataFrame, b: pd.DataFrame) -> tuple[bool, list]:
    """逐列逐欄逐位元：欄名欄序、列數、dtype、值（NaN 對 NaN 算相同；浮點比位元組）。回 (是否相同, 不同的欄)。"""
    if list(a.columns) != list(b.columns) or len(a) != len(b):
        return False, ["<columns/len>"]
    bad = []
    for c in a.columns:
        x, y = a[c].reset_index(drop=True), b[c].reset_index(drop=True)
        if x.dtype != y.dtype:
            bad.append(f"{c}:dtype {x.dtype}≠{y.dtype}"); continue
        if x.dtype.kind == "f":
            xv, yv = x.to_numpy(np.float64), y.to_numpy(np.float64)
            xn, yn = np.isnan(xv), np.isnan(yv)
            same = np.array_equal(xn, yn) and np.array_equal(np.where(xn, 0.0, xv).view(np.int64), np.where(yn, 0.0, yv).view(np.int64))
        else:
            same = x.equals(y)
        if not same:
            bad.append(c)
    return not bad, bad


def build_ext(procs: int = 2, log=print) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """回 (延伸面板, 同一次 build_panel 重算的舊量測日那一段, 資訊)。延伸面板已遮 fwd（E2）、欄序同舊面板。"""
    cal = D.load_calendar()
    U = load_gate3()
    allp, newp = positions(cal)
    log(f"[延伸] 快照 {H2.SHA[:10]}｜gate3 {len(U)} 檔｜量測日 {len(allp)} 個（{cal[allp[0]].date()}～{cal[allp[-1]].date()}），"
        f"新增 {len(newp)} 個：{', '.join(str(cal[p].date()) for p in newp)}")
    panel, M = RP4.build_panel(cal, U, allp, procs=procs, log=log)
    if len(M):
        raise SystemExit(f"⛔ min_periods 常設斷言不成立（{len(M)} 列）⇒ 停：{M.head(3).to_dict('records')}")
    panel = mask_fwd(panel)                                                 # E2：⛔ 任何人看之前
    old = P.read_panel(OLD_PANEL)
    if set(panel.columns) != set(old.columns):
        raise SystemExit(f"⛔ 欄位集合不同：多 {set(panel.columns) - set(old.columns)}、少 {set(old.columns) - set(panel.columns)}")
    panel = panel[list(old.columns)]
    re_old = panel[panel["measure_date"] <= pd.Timestamp(OLD_END)].reset_index(drop=True)
    new = panel[panel["measure_date"] > pd.Timestamp(OLD_END)].reset_index(drop=True)
    # 讀回來的 dtype 對齊：寫檔再讀（與舊面板同一條路）⇒ 比對的是「檔案上的值」
    buf = io.StringIO(); re_old.to_csv(buf, index=False); buf.seek(0)
    re_old_rt = pd.read_csv(buf, dtype={"stock_id": str}, parse_dates=["measure_date"], float_precision="round_trip")
    ok, bad = frames_identical(re_old_rt, old)
    if not ok:
        raise SystemExit(f"⛔ E3：重算的舊量測日那一段 ≠ 舊面板（{bad}）⇒ 停、不寫檔")
    ext = pd.concat([old, new], ignore_index=True)
    ext = ext.sort_values(["measure_date", "stock_id"], kind="stable").reset_index(drop=True)
    info = {"sha": H2.SHA, "gate3": len(U), "n_md": len(allp), "new_md": [str(cal[p].date()) for p in newp],
            "rows_old": len(old), "rows_new": len(new), "rows_ext": len(ext)}
    return ext, re_old, info


def write_panel(df: pd.DataFrame, path: str) -> None:
    """E4：gzip mtime＝0 ⇒ 可重現的 sha256。"""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    df.to_csv(path, index=False, compression={"method": "gzip", "mtime": 0})


def sha256(path: str) -> tuple[str, int]:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest(), os.path.getsize(path)


def panel_facts(path: str) -> dict:
    df = P.read_panel(path)
    md = df["measure_date"]
    return {"rows": len(df), "md_min": str(md.min().date()), "md_max": str(md.max().date()), "n_md": int(md.nunique()),
            "eligible": int(df["eligible"].astype(bool).sum())}


def sha_section() -> str:
    """PANEL_SHA.md 檔尾要加的一節（⛔ 不刪原內容）。"""
    import subprocess
    head = subprocess.run(["git", "rev-parse", "--short=10", "HEAD"], capture_output=True, text=True).stdout.strip()
    now = pd.Timestamp.now(tz="Asia/Taipei").strftime("%Y-%m-%d %H:%M")
    L = ["", "## 延伸面板 panel_ext（裁定線 seq167 §四：面板補 2026-04～08 量測日；新 sha 與舊 sha 並列）", "",
         f"量測 {now}（台北）；工作樹 `~/tw-p17`（HEAD {head}，分支 claude/stock-analysis-backtest-iv9xji）。",
         "由 `python backtest/p9_panel_ext.py --sha` 產生（hashlib.sha256 讀整個檔的位元組）。", "",
         "| 項 | resultsp4/panel.csv.gz（舊，P8 用） | resultsAFC/panel.csv.gz（舊，主窗） | **resultsp9_engine/panel_ext.csv.gz（新）** |",
         "|---|---|---|---|"]
    rows = {}
    for p in (OLD_PANEL_P4, OLD_PANEL, OUT):
        s, n = sha256(p); f = panel_facts(p)
        blob = subprocess.run(["git", "hash-object", p], capture_output=True, text=True).stdout.strip()
        tracked = subprocess.run(["git", "ls-files", "--error-unmatch", p], capture_output=True, text=True).returncode == 0
        rows[p] = dict(sha=s, n=n, blob=blob, tracked=tracked, **f)
    a, b, c = (rows[p] for p in (OLD_PANEL_P4, OLD_PANEL, OUT))
    fmt = lambda r, k: {"sha": f"`{r['sha']}`", "n": f"{r['n']:,} B", "blob": f"`{r['blob']}`",
                        "tracked": "是" if r["tracked"] else "否（未入庫；本件不 commit）",
                        "rows": f"{r['rows']:,}", "md": f"{r['md_min']}～{r['md_max']}（{r['n_md']} 個）",
                        "eligible": f"{r['eligible']:,}"}[k]
    for lab, k in (("**sha256**", "sha"), ("位元組數", "n"), ("git hash-object", "blob"), ("進 git？", "tracked"),
                   ("列數", "rows"), ("量測日", "md"), ("eligible 列", "eligible")):
        L.append(f"| {lab} | {fmt(a, k)} | {fmt(b, k)} | {fmt(c, k)} |")
    L += ["",
          f"- 資料：main `{H2.SHA}` 快照（~/h2data/<sha>/data，唯讀）＝ resultsAFC 同一份；母體 gate3 全體；`researchp4.build_panel` 同一支。",
          "- panel_ext ＝ resultsAFC/panel.csv.gz 的全部列（讀回原樣）＋ 新增量測日 2026-04-01、05-04、06-01、07-01、08-03 的列；欄名欄序與 resultsAFC 完全相同。",
          "- ⛔ 新增量測日的 fwd_20／fwd_60／fwd_120 一律 NaN（本件只為 2-B ⓑ 旗標，⛔ 不讀不存報酬）。",
          "- 重疊處（2026-03-02 以前）與 resultsAFC 逐列逐欄逐位元相同：fixture `backtest/selftest_p9_panel_ext.py`（結果 `panel_ext_fixtures.json`）。",
          "- panel_ext 的 gzip 標頭 mtime＝0 ⇒ 同內容、同檔名 panel_ext.csv.gz 重寫 sha 不變（已驗：讀回再寫到別的目錄同名檔，sha 相同；gzip 標頭含檔名，換名就變）；兩份舊面板是 pandas 預設（mtime＝寫檔時間），⛔ 不能拿重寫的檔對它們的 sha，要比內容。",
          "- ⚠ resultsp4 那一份是分支舊快照、母體不是 gate3，與另兩份不同源，只並列備查（P8、P9 回歸閘 2 用它）。", ""]
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--procs", type=int, default=2)
    ap.add_argument("--sha", action="store_true", help="只算三份 panel 的 sha256 並在 PANEL_SHA.md 檔尾加一節")
    a = ap.parse_args()
    if a.sha:
        p = os.path.join(OUT_DIR, "PANEL_SHA.md")
        txt = open(p, encoding="utf-8").read()
        if "## 延伸面板 panel_ext" in txt:
            raise SystemExit("⛔ PANEL_SHA.md 已有延伸面板一節 ⇒ 不重複追加（要重記請人工處理）")
        sec = sha_section()
        with open(p, "a", encoding="utf-8") as f:
            f.write(sec)
        print(sec)
        return
    t0 = time.time()
    ext, _, info = build_ext(a.procs, log=lambda s: print(s, flush=True))
    write_panel(ext, OUT)
    back = P.read_panel(OUT)
    ok, bad = frames_identical(back, ext)
    assert ok, f"寫出再讀回不同：{bad}"
    print(f"✅ {OUT}：{info}｜{time.time() - t0:.0f}s", flush=True)


if __name__ == "__main__":
    main()

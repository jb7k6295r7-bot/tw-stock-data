"""forward_p4 冒煙自測（暫存目錄、--limit 60）：① 寫完重讀列數＝合格檔數；② 同一量測日第二次跑不重寫；③ 累積名單只增不減；
④ 特徵只看 ≤ 量測日、open_next＝次日開盤；⑤ 型號沒中心就空。rc != 0 或輸出含 ✗ 才算紅。"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FAIL = 0


def check(cond, msg):
    global FAIL
    print(("  ✓ " if cond else "  ✗ ") + msg)
    if not cond:
        FAIL += 1


def run(args):
    return subprocess.run([sys.executable, "-m", "backtest.forward_p4", *args], cwd=ROOT, capture_output=True, text=True)


if __name__ == "__main__":
    out = tempfile.mkdtemp(prefix="fp4_")
    try:
        r = run(["--date", "2026-08-01", "--out", out, "--limit", "60", "--procs", "2", "--centers", "none", "--allow-before-v1"])
        check(r.returncode == 0, f"第一趟 rc={r.returncode} {r.stderr[-200:]}")
        rec = pd.read_csv(os.path.join(out, "records.csv"), dtype={"stock_id": str})
        uni = pd.read_csv(os.path.join(out, "universe.csv"), dtype=str)
        check(len(rec) > 0 and (rec["measure_date"] == "2026-08-03").all(), f"量測日＝2026-08-03（8 月第一個交易日），{len(rec)} 檔")
        check((rec["entry_date"] == "2026-08-04").all() and rec["open_next"].notna().all(), "進場日 08-04、open_next 有值")
        check(rec["type"].isna().all() and (rec["centers_version"].isna() | (rec["centers_version"] == "")).all(), "--centers none ⇒ 型號空")
        check(set(uni["stock_id"]) == set(rec["stock_id"]) and (uni["first_seen"] == "2026-08-03").all(), "累積名單＝本趟合格檔")
        check(rec["asof"].notna().all() and rec["data_sha"].str.len().eq(40).all(), "asof／data_sha 有值")
        n1 = len(rec)
        r2 = run(["--date", "2026-08-15", "--out", out, "--limit", "60", "--procs", "2", "--centers", "none", "--allow-before-v1"])
        rec2 = pd.read_csv(os.path.join(out, "records.csv"), dtype={"stock_id": str})
        check(r2.returncode == 0 and len(rec2) == n1 and "冪等" in r2.stderr, "同月第二次跑不重寫（冪等）")
        r3 = run(["--date", "2026-09-01", "--out", out, "--limit", "60", "--procs", "2", "--allow-before-v1"])
        rec3 = pd.read_csv(os.path.join(out, "records.csv"), dtype={"stock_id": str}); uni3 = pd.read_csv(os.path.join(out, "universe.csv"), dtype=str)
        check(r3.returncode == 0 and (rec3["measure_date"] == "2026-09-01").sum() > 0, "9 月再跑一趟 ⇒ 追加列")
        check(len(uni3) >= len(uni) and set(uni["stock_id"]) <= set(uni3["stock_id"]), f"累積名單只增不減 {len(uni)} → {len(uni3)}")
        r9 = rec3[rec3["measure_date"] == "2026-09-01"]
        check(r9["type"].dropna().astype(int).isin([0, 1, 2, 3]).all() and r9["type"].notna().all() and r9["centers_version"].str.contains("23be85b004977222").all(),
              f"預設 auto 中心 ⇒ 型號 0～3 全填、centers_version 帶 sha16（{r9['type'].value_counts().to_dict()}）")
        out5 = tempfile.mkdtemp(prefix="fp4v1_")
        r5 = run(["--date", "2026-09-01", "--out", out5, "--limit", "5"])
        check(r5.returncode == 2 and "早於前瞻 v1 起始月" in r5.stderr and not os.path.exists(os.path.join(out5, "records.csv")), "⛔ 沒有 --allow-before-v1：2026-09 早於 V1_START ⇒ rc=2、不寫任何檔")
        shutil.rmtree(out5, ignore_errors=True)
        # 沒有次日資料的月份要擋
        r4 = run(["--date", "2030-01-01", "--out", out, "--limit", "5"])
        check(r4.returncode != 0, "日曆外的月份 ⇒ 紅、不寫")
    finally:
        shutil.rmtree(out, ignore_errors=True)
    print("結果：", "全綠" if FAIL == 0 else f"✗ {FAIL} 條")
    sys.exit(1 if FAIL else 0)

# 突變：把 records 的冪等檢查拿掉 ⇒ 冪等條紅；update_universe 改成整檔取代 ⇒ 只增不減條紅；V1_START 改 2026-01 ⇒ 下限條紅；load_centers 的 centers_z 改讀 centers ⇒ 型號條炸

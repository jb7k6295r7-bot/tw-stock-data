# -*- coding: utf-8 -*-
"""母體閘門與快照戳記 —— 落地裁定線 20260924-2051（seq85）§一③ 的【工具】那一半。

裁定 §一③ 逐字：
    「今後在分支上跑 ⇒ 要嘛先同步 data/ 到 main，要嘛明文排除名稱含 -DR ⇒ **二選一寫進登錄**」

⛔ 本線不自訂登錄條文（⛔ 不訂門檻、⛔ 不自取條號）——
⭐ 本支只提供讓那兩個選項【可以被機器執行】的函式，讓登錄可以指名它：

    (甲) 先同步 data/ 到 main   ⇒ require_snapshot_at_least("2026-09-21")
    (乙) 明文排除名稱含 -DR     ⇒ uni = exclude_dr(uni)

並提供每份報告都該印的一行：

    snapshot_stamp()  ⇒ "data/ 快照 2026-09-18（stocks.csv blob cb01b28f…；-DR 落在 kind=='stock' 的 7 檔）"

⭐ 用法（在任何 research*.py 的開頭）：
    from backtest import universe_gate as UG
    uni = D.load_universe()
    uni = UG.exclude_dr(uni)          # (乙)
    print(UG.snapshot_stamp())        # ⇒ 抄進報告的腳註
"""
from __future__ import annotations
import os
import subprocess
import pandas as pd

from . import data as D

STOCKS = os.path.join(D.DATA, "meta", "stocks.csv")
#  ⭐ main 上這 7 檔改成 dr 的那一版（逐版查出來的變動點；本線 20260924-2044 §四）
FLIP_LAST_STOCK = "2026-09-18"   # 75ff13d98：最後一個還是 stock 的版本
FLIP_FIRST_DR = "2026-09-21"     # d5b2094e1：最早一個是 dr 的版本


def _read_stocks() -> pd.DataFrame:
    return pd.read_csv(STOCKS, dtype=str)


def snapshot_date() -> str:
    """這一份 stocks.csv 的快照時點 ＝ last_seen 欄的最大值（⭐ 而不是檔案 mtime）。

    ⚠ 用 mtime 會被 git checkout／rsync 改掉 ⇒ ⛔ 不可靠；last_seen 是資料自己說的。
    """
    s = _read_stocks()
    return str(pd.to_datetime(s["last_seen"], errors="coerce").max().date())


def dr_in_universe() -> pd.DataFrame:
    """名稱含 `-DR` 而落在 `kind=='stock'` ∧ `market∈{twse,tpex}` 母體裡的檔（⭐ 正常應該是空的）。"""
    s = _read_stocks()
    m = (s["kind"] == "stock") & s["market"].isin(["twse", "tpex"]) & s["name"].str.contains("-DR", na=False)
    return s.loc[m, ["stock_id", "name", "market", "kind", "first_seen", "last_seen"]].reset_index(drop=True)


def snapshot_stamp() -> str:
    """報告腳註用的一行（⭐ 每份用分支 data/ 的交件都該印）。"""
    d = snapshot_date()
    bad = dr_in_universe()
    try:
        blob = subprocess.run(["git", "hash-object", STOCKS], capture_output=True, text=True,
                              cwd=os.path.dirname(D.DATA) or ".").stdout.strip()[:8]
    except Exception:
        blob = "?"
    if len(bad) == 0:
        return "data/ 快照 {}（stocks.csv blob {}…；-DR 落在 kind=='stock' 的 0 檔 ✅）".format(d, blob)
    return ("data/ 快照 {}（stocks.csv blob {}…；⚠ -DR 落在 kind=='stock' 的 {} 檔：{}）"
            .format(d, blob, len(bad), "／".join(bad["stock_id"])))


def require_snapshot_at_least(day: str = FLIP_FIRST_DR) -> str:
    """(甲) 要求 data/ 至少新到 `day`（預設 ＝ main 上 -DR 改成 dr 的那一版）。

    ⛔ 不夠新就中止 —— ⭐ 而訊息裡直接寫出補救動作，⛔ 不只說「失敗」。
    """
    d = snapshot_date()
    assert d >= day, (
        "⛔ data/ 快照 {} 比要求的 {} 舊 ⇒ 依裁定線 seq85 §一③(甲) 不可在這份資料上開跑。\n"
        "   ⇒ 補救：把 data/ 同步到 origin/main，或改走 (乙) uni = universe_gate.exclude_dr(uni)".format(d, day))
    return d


def exclude_dr(uni: pd.DataFrame) -> pd.DataFrame:
    """(乙) 明文排除名稱含 `-DR` 的（⭐ 依名稱，⛔ 不依 kind）。

    ⛔ 不可以只寫 `kind != 'dr'`：資料庫線 20260924-2035 §二 已證明 `kind=='dr'`
       只抓到 13／21 檔 DR（另 8 檔六碼已停交易的落在 `other`）。
    ⭐ 所以這裡用【名稱含 -DR】，它對兩種快照都成立。
    """
    assert "name" in uni.columns, "⛔ 需要 name 欄才能依名稱排除"
    n0 = len(uni)
    out = uni[~uni["name"].str.contains("-DR", na=False)].reset_index(drop=True)
    print("[母體閘門] 依名稱排除 -DR：{:,} ⇒ {:,} 檔（剔 {} 檔）".format(n0, len(out), n0 - len(out)))
    return out


def _selftest():
    print("=== universe_gate 自測 ===")
    d = snapshot_date()
    print("  snapshot_date() ＝ {}".format(d))
    bad = dr_in_universe()
    print("  dr_in_universe() ＝ {} 檔".format(len(bad)))
    if len(bad):
        print(bad.to_string(index=False))
    print("  snapshot_stamp() ⇒ {}".format(snapshot_stamp()))

    uni = D.load_universe()
    n0 = len(uni)
    out = exclude_dr(uni)
    #  ⭐ 斷言：剔掉的檔數必須等於 dr_in_universe() 數出來的
    assert n0 - len(out) == len(bad), \
        "⛔ exclude_dr 剔 {} 檔，dr_in_universe 說 {} 檔 ⇒ 兩邊對不上".format(n0 - len(out), len(bad))
    #  ⭐ 斷言：剔完之後再數一定是 0
    assert not out["name"].str.contains("-DR", na=False).any(), "⛔ 剔完還有 -DR"
    print("  ✅ exclude_dr 的剔除數與 dr_in_universe 一致，且剔完為 0")

    #  ⭐ (甲) 那道必須在【現在這份舊快照】上真的擋下來 —— ⛔ 否則它是空轉的
    try:
        require_snapshot_at_least(FLIP_FIRST_DR)
    except AssertionError as e:
        print("  ✅ require_snapshot_at_least('{}') 在快照 {} 上【確實擋下來】".format(FLIP_FIRST_DR, d))
        print("     訊息首行：{}".format(str(e).split(chr(10))[0]))
    else:
        assert d >= FLIP_FIRST_DR, "⛔ 快照比要求舊，(甲) 卻沒擋 ⇒ 那道閘門是空轉的"
        print("  ✅ 快照 {} 已 ≥ {} ⇒ (甲) 通過".format(d, FLIP_FIRST_DR))
    #  ⭐ 而它必須在一個【一定過】的門檻上放行 ⇒ 證明它不是「永遠擋」
    got = require_snapshot_at_least("2000-01-01")
    assert got == d
    print("  ✅ 同一道閘門在 2000-01-01 的門檻上放行 ⇒ ⛔ 不是「永遠擋」")
    print()
    print("⭐ 兩個選項都可機器執行；⏳ 二選一【寫進登錄】是策略線／裁定線的格子，⛔ 本線不自取。")


if __name__ == "__main__":
    _selftest()

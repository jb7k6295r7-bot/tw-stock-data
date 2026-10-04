# -*- coding: utf-8 -*-
"""母體閘門與快照戳記 —— 落地裁定線 20260924-2051（seq85）§一③ 的【工具】那一半。

裁定 §一③ 逐字：
    「今後在分支上跑 ⇒ 要嘛先同步 data/ 到 main，要嘛明文排除名稱含 -DR ⇒ **二選一寫進登錄**」

⛔ 本線不自訂登錄條文（⛔ 不訂門檻、⛔ 不自取條號）——
⭐ 本支只提供讓那兩個選項【可以被機器執行】的函式，讓登錄可以指名它：

    (甲) 先同步 data/ 到 main   ⇒ require_snapshot_at_least("2026-09-21")
    (乙) 明文排除名稱含 -DR     ⇒ uni = exclude_dr(uni)

⭐ 裁定線 seq87 §二 裁「甲乙不等價、都不夠 ⇒ 三道都要」，seq90 §三 指定第三道用名稱：
    (丙) 明文排除創新板          ⇒ uni = exclude_innovation(uni)（名稱含 -創）
    三道一起                     ⇒ uni = gate3(main_stocks())

⭐ 沿革（裁定線 seq271 §二，2026-09-28）：創新板名稱另有「-KY創」（6854 錼創科技-KY創、6924 榮惠-KY創、7823 奧義賽博-KY創、7827 漢康-KY創），
   舊第三道只認「-創」⇒ 漏掉這 4 檔。補認「-KY創」只對之後新跑的件生效：開關 innov_ky，⭐ 預設關（關 ⇒ 既有路徑逐位元不變）；已判件不重跑。
   開法（新跑的件擇一）：① 程式開頭 UG.set_innov_ky(True)（全域預設；之後所有 gate3／exclude_innovation 呼叫都生效）
                         ② 單次呼叫 gate3(stocks, innov_ky=True)／exclude_innovation(uni, innov_ky=True)
   ⚠ 開關只影響【當下呼叫 gate3 的那一步】；用快取訊號／面板（例 resultsN17/sig_edc6f、resultsAFC/panel、resultsp9_engine/panel_ext）的件要重建快取才會真的剔掉這 4 檔

⭐ 沿革（裁定 seq293 §二，2026-10-04；回測線自查 7b34b0e460「資料庫 1435 體檢三陷阱」⑥ 的修正）：新口徑總開關 GATE_V2，⭐ 預設關（關 ⇒ 既有路徑逐位元不變）
   開法：程式開頭 UG.set_gate_v2(True)（只給新件；舊件重現一律不開）。開了以後一次生效三項：
   ① 創新板改依【當日名稱】判、只剔在板期間（innov_pit）：stocks/<代號>.csv 每列的 name 欄含「-創」或「-KY創」的那些日子無效；
      靜態母體只剔「整段都在板（沒有任何一天是板外上市櫃列）」的股票（例 6854 錼創科技-KY創）；
      轉板股（例 6423 億而得：2024-05-15～2026-01-21 名「億而得-創」、2026-01-22 轉上櫃）留在靜態母體，板期由 pit_valid 剔
      ⚠ 本快照沒有官方板別欄 ⇒ 用逐日檔的當時名稱（6423 已驗：轉板前後名稱不同）；資料庫 1435 說 data/universe/daily 的名稱是現名 ⇒ ⛔ 不可改讀那一份
   ② innov_ky：GATE_V2 開時「-KY創」一律算創新板（＝ 新件預設開；舊件照 INNOV_KY 原值，預設關）
   ③ 逐列市場：stocks/<代號>.csv 每列的 market 欄不是 twse／tpex 的日子（例 7812 上市前 2026-09-03～09-21 的 12 天興櫃列）無效
   ⇒ 新函式：set_gate_v2、row_ok、pit_valid、pit_table、filter_pit（訊號表剔除訊號日無效的列）；gate3 在開時走 _gate3_v2
   ⚠ 與 innov_ky 一樣：開關只影響「當下呼叫的那一步」；用快取訊號／面板的件要嘛重建快取、要嘛對訊號表套 filter_pit
   閘門（本線 2026-10-04）：G1 不開時 營量 v1 T1（resultsT1fix c13 r0）、營飆 v1（c1 r0～4）、daily_list 產出逐位元相同；
     G2 開時 fixture（6423、6854、7812、一般股、合成股）全過且各附會紅的反例（python -m backtest.universe_gate v2）；G3 見 resultsGateV2/REPORT.md

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


INNOV_KY = False                 # ⭐ 裁定 seq271 §二：預設關（關 ⇒ 與舊版逐位元相同）；開 ⇒ 另剔名稱含「-KY創」
INNOV_KY_RE = r"-(?:KY)?創"      # 開的時候用：名稱含「-創」或「-KY創」


def set_innov_ky(on: bool) -> None:
    """全域預設切換（新跑的件在程式開頭呼叫一次）。"""
    global INNOV_KY
    INNOV_KY = bool(on)


def exclude_innovation(uni: pd.DataFrame, innov_ky: bool | None = None) -> pd.DataFrame:
    """第三道閘（裁定線 seq90 §三）：明文排除【創新板】—— 依名稱含 `-創`。

    ⭐ 與 exclude_dr 同一種做法：依【名稱】，⛔ 不靠會隨快照變的派生欄（裁定線 seq90 §三 指定）。
    ⭐ 依據：裁定線 1611 §二 裁創新板剔除；而 (甲) 同步到 main 會把 7812 稜研科技*-創 帶進來。
    ⭐ innov_ky（裁定 seq271 §二）：None ⇒ 用全域 INNOV_KY（預設 False）；True ⇒ 名稱含「-創」或「-KY創」都剔。
    """
    assert "name" in uni.columns, "⛔ 需要 name 欄才能依名稱排除"
    on = (INNOV_KY or GATE_V2) if innov_ky is None else bool(innov_ky)      # 裁定 seq293 §二 ②：GATE_V2 關 ⇒ ＝ INNOV_KY（逐位元同舊）
    n0 = len(uni)
    if not on:                                           # ⭐ 舊路徑，一字未動
        out = uni[~uni["name"].str.contains("-創", na=False, regex=False)].reset_index(drop=True)
        print("[母體閘門] 依名稱排除創新板（-創）：{:,} ⇒ {:,} 檔（剔 {} 檔）".format(n0, len(out), n0 - len(out)))
        return out
    out = uni[~uni["name"].str.contains(INNOV_KY_RE, na=False, regex=True)].reset_index(drop=True)
    print("[母體閘門] 依名稱排除創新板（-創／-KY創；innov_ky 開）：{:,} ⇒ {:,} 檔（剔 {} 檔）".format(n0, len(out), n0 - len(out)))
    return out


def universe_from_stocks(stocks: pd.DataFrame) -> pd.DataFrame:
    """與 data.load_universe() 同一條件（kind=='stock' ∧ market∈{twse,tpex}），但吃任意一份 stocks 表
    ⇒ 讓閘門可以在【main 快照】上驗，⛔ 不限於本線分支的舊快照。"""
    return stocks[(stocks["kind"] == "stock") & stocks["market"].isin(["twse", "tpex"])].reset_index(drop=True)


def main_stocks() -> pd.DataFrame:
    """讀 origin/main 的 data/meta/stocks.csv（⭐ data/ 以 main 為準，seq85 §三③）。"""
    import io as _io
    root = os.path.dirname(D.DATA)
    txt = subprocess.run(["git", "show", "origin/main:data/meta/stocks.csv"], capture_output=True,
                         text=True, cwd=root).stdout
    assert txt.startswith("stock_id"), "⛔ 讀不到 origin/main 的 stocks.csv"
    return pd.read_csv(_io.StringIO(txt), dtype=str)


def gate3(stocks: pd.DataFrame, innov_ky: bool | None = None) -> pd.DataFrame:
    """三道閘一起（裁定線 seq87 §二、seq90 §三）：母體條件 → 排除 -DR → 排除創新板。
    ⚠ 第一道「data/ 用 main」由呼叫方決定傳哪一份 stocks（建議 main_stocks()）。
    ⭐ innov_ky：None ⇒ 全域 INNOV_KY（預設關）；見 exclude_innovation。
    ⭐ GATE_V2 開（裁定 seq293 §二）⇒ 走 _gate3_v2（創新板只剔整段在板者；板期與興櫃列由 pit_valid／filter_pit 剔）。"""
    if GATE_V2:
        return _gate3_v2(stocks)
    return exclude_innovation(exclude_dr(universe_from_stocks(stocks)), innov_ky=innov_ky)


# ═════════════ 新口徑（裁定 seq293 §二；GATE_V2 預設關）═════════════
GATE_V2 = False
BOARD_RE = INNOV_KY_RE           # 「-創」或「-KY創」
LISTED = ("twse", "tpex")
_ROWS: dict = {}


def set_gate_v2(on: bool) -> None:
    """新口徑總開關（①當日名稱判創新板、只剔板期 ②-KY創 算創新板 ③逐列市場擋興櫃列）。⭐ 只給新件；舊件重現不開。"""
    global GATE_V2
    GATE_V2 = bool(on)


def _rows(sid: str, data: str | None = None):
    """stocks/<代號>.csv 的 date、name、market（快取）；檔不存在 ⇒ None。"""
    data = data or D.DATA
    k = (data, sid)
    if k not in _ROWS:
        p = os.path.join(data, "stocks", f"{sid}.csv")
        if not os.path.exists(p):
            _ROWS[k] = None
        else:
            df = pd.read_csv(p, dtype=str, usecols=lambda c: c in ("date", "name", "market"))
            df = df.drop_duplicates("date", keep="last")
            df["date"] = pd.to_datetime(df["date"])
            _ROWS[k] = df.sort_values("date").reset_index(drop=True)
    return _ROWS[k]


def row_ok(sid: str, data: str | None = None):
    """每一列是否有效（Series，index ＝ 日期）：market ∈ twse／tpex ∧ 當日名稱不含「-創」「-KY創」。檔不存在 ⇒ None。"""
    df = _rows(sid, data)
    if df is None:
        return None
    mk = df["market"].isin(LISTED) if "market" in df else pd.Series(True, index=df.index)
    nm = ~df["name"].fillna("").str.contains(BOARD_RE, regex=True) if "name" in df else pd.Series(True, index=df.index)
    return pd.Series((mk & nm).to_numpy(bool), index=pd.DatetimeIndex(df["date"]))


def pit_valid(sid: str, cal, data: str | None = None):
    """日曆長布林：該日是否在新口徑母體內。有列的日子照 row_ok；沒列的日子（停牌）沿用前一列狀態；第一列之前 ⇒ True（中性）。
    ⭐ GATE_V2 關 ⇒ 全 True（不作用）。"""
    import numpy as np
    n = len(cal)
    if not GATE_V2:
        return np.ones(n, bool)
    r = row_ok(sid, data)
    if r is None or len(r) == 0:
        return np.ones(n, bool)
    s = r.astype(float).reindex(pd.DatetimeIndex(cal).union(r.index)).ffill().reindex(pd.DatetimeIndex(cal))
    return np.where(s.isna(), True, s.to_numpy() > 0.5)


def pit_table(sids, cal, data: str | None = None) -> dict:
    return {s: pit_valid(s, cal, data) for s in sids}


def filter_pit(sig: pd.DataFrame, cal, sid_col: str = "sid", pos_col: str = "entry_pos", lag: int = 1, data: str | None = None) -> pd.DataFrame:
    """訊號表：剔除「訊號日（pos_col − lag，預設 ＝ 進場前一個交易日）」不在新口徑母體內的列。⭐ GATE_V2 關 ⇒ 原表照回。"""
    if not GATE_V2 or len(sig) == 0:
        return sig
    tab = pit_table(sorted(set(sig[sid_col].astype(str))), cal, data)
    keep = [bool(tab[str(s)][int(p) - lag]) if 0 <= int(p) - lag < len(cal) else True for s, p in zip(sig[sid_col], sig[pos_col])]
    out = sig[keep].reset_index(drop=True)
    print("[母體閘門 v2] 訊號表剔除板期／興櫃列：{:,} ⇒ {:,} 列（剔 {}）".format(len(sig), len(out), len(sig) - len(out)))
    return out


def _gate3_v2(stocks: pd.DataFrame, data: str | None = None) -> pd.DataFrame:
    """新口徑靜態母體：kind＝stock ∧ market∈twse／tpex → 排除 -DR → 創新板只剔「沒有任何一列是板外上市櫃列」者
    （逐日檔不存在 ⇒ 退回現名判「-創／-KY創」）。板期、興櫃列 ⇒ pit_valid／filter_pit。"""
    uni = exclude_dr(universe_from_stocks(stocks))
    n0 = len(uni); keep = []
    for s, nm in zip(uni["stock_id"], uni["name"]):
        r = row_ok(s, data)
        if r is None:
            keep.append(not pd.Series([nm]).str.contains(BOARD_RE, regex=True, na=False).iloc[0])
        else:
            keep.append(bool(r.any()))
    out = uni[keep].reset_index(drop=True)
    print("[母體閘門 v2] 創新板只剔整段在板／無上市櫃列者：{:,} ⇒ {:,} 檔（剔 {} 檔）；板期與興櫃列由 pit_valid 剔".format(n0, len(out), n0 - len(out)))
    return out


def _selftest_gate3():
    print()
    print("=== 第三道閘（創新板，依名稱 -創）自測：⭐ 在 main 快照上驗 ===")
    ms = main_stocks()
    um = universe_from_stocks(ms)
    inn = um[um["name"].str.contains("-創", na=False, regex=False)]
    print("  main 母體 {:,} 檔；其中名稱含 -創 的 {} 檔：{}".format(
        len(um), len(inn), "、".join(inn["stock_id"] + " " + inn["name"])))
    #  ① 7812 必須在 main 母體裡（否則「必須被剔」是空話），而且必須被剔
    assert "7812" in set(um["stock_id"]), "⛔ 7812 不在 main 母體 ⇒ 這條自測沒有鑑別力"
    g = gate3(ms)
    assert "7812" not in set(g["stock_id"]), "⛔ 7812 稜研科技*-創 沒被剔"
    print("  ✅ 7812 在 main 母體裡，且被第三道閘剔除")
    #  ② 另造一檔名稱不帶 -創 的 fixture ⇒ 必須留
    fx = pd.DataFrame([
        dict(stock_id="99991", name="測試創意公司", market="twse", kind="stock",
             first_seen="2020-01-01", last_seen="2026-09-23"),   # 名稱有「創」但沒有「-創」⇒ 必須留
        dict(stock_id="99992", name="測試科技*-創", market="twse", kind="stock",
             first_seen="2020-01-01", last_seen="2026-09-23"),   # 必須剔
        dict(stock_id="99993", name="測試存託-DR", market="twse", kind="stock",
             first_seen="2020-01-01", last_seen="2026-09-23"),   # 第二道閘必須剔
    ])
    gf = gate3(fx)
    assert list(gf["stock_id"]) == ["99991"], "⛔ fixture 結果不對：{}".format(list(gf["stock_id"]))
    print("  ✅ fixture：「測試創意公司」（有『創』無『-創』）留；「*-創」剔；「-DR」剔")
    print("  ⇒ 三道閘在 main 快照上：{:,} ⇒ {:,} 檔".format(len(um), len(g)))


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


def _selftest_gate_v2(snap: str | None = None):
    """G2（裁定 seq293 §二）：開 GATE_V2 的 fixture；每條斷言另驗「關掉修正（舊口徑）或故意弄壞 ⇒ 會紅」。
    snap ＝ 價格快照 data 目錄（預設 edc6f8002f）；另造一份合成資料夾驗「現名 -創 但以前不在板」。"""
    import shutil
    import tempfile
    import numpy as np
    global GATE_V2
    snap = snap or os.path.expanduser("~/h2data/edc6f8002fed8803795e3486ad57db513f7e9f65/data")
    old = GATE_V2
    res = []

    def check(name, fn_pass, fn_red):
        ok = bool(fn_pass()); red = not bool(fn_red())
        res.append((name, ok, red))
        print("  {} {}｜反例會紅：{}".format("✅" if ok else "⛔", name, "✅" if red else "⛔（沒有鑑別力）"))
    try:
        stocks = pd.read_csv(os.path.join(snap, "meta", "stocks.csv"), dtype=str)
        cal = pd.DatetimeIndex(sorted(set(pd.to_datetime(pd.read_csv(os.path.join(snap, "stocks", "2330.csv"), usecols=["date"])["date"]))
                                      | set(pd.to_datetime(pd.read_csv(os.path.join(snap, "stocks", "7812.csv"), usecols=["date"])["date"]))))
        pos = lambda d: int(cal.searchsorted(pd.Timestamp(d)))

        def with_v2(on, f):
            global GATE_V2
            b = GATE_V2; GATE_V2 = on
            try:
                return f()
            finally:
                GATE_V2 = b
        g_new = with_v2(True, lambda: set(_gate3_v2(stocks, snap)["stock_id"]))
        g_old = with_v2(False, lambda: set(gate3(stocks)["stock_id"]))
        v6423 = lambda on: with_v2(on, lambda: pit_valid("6423", cal, snap))
        print("=== G2 新口徑 fixture（快照 {}）===".format(snap))
        check("6423 板期 2024-05-15～2026-01-21 每天無效、2026-01-22 起有效、且留在靜態母體",
              lambda: "6423" in g_new and not v6423(True)[pos("2024-05-15"):pos("2026-01-21") + 1].any() and v6423(True)[pos("2026-01-22"):].all(),
              lambda: not v6423(False)[pos("2024-05-15"):pos("2026-01-21") + 1].any())             # 舊口徑：板期全有效 ⇒ 會紅
        check("6854 錼創科技-KY創 整段在板 ⇒ 靜態母體剔除",
              lambda: "6854" not in g_new, lambda: "6854" not in g_old)                             # 舊口徑（innov_ky 關）收進來 ⇒ 會紅
        v7812 = lambda on: with_v2(on, lambda: pit_valid("7812", cal, snap))
        r7812 = _rows("7812", snap); em = [pos(d) for d in r7812.loc[r7812["market"] == "emerging", "date"]]
        check("7812 上市前 12 天興櫃列（2026-09-03～09-21）每一列都無效",
              lambda: len(em) == 12 and not v7812(True)[em].any(),
              lambda: not v7812(False)[em].any())
        v2330 = lambda: with_v2(True, lambda: pit_valid("2330", cal, snap))
        check("一般股 2330 每天有效且在靜態母體",
              lambda: "2330" in g_new and v2330().all(),
              lambda: _broken_all_board("2330", cal, snap).all())                                     # 故意把每列都當板內 ⇒ 會紅
        check("新口徑靜態母體 ＝ 舊口徑 − 6854、6924、7823、7827（四檔 -KY創）；6423 兩邊都在（板期改由 pit_valid 剔）",
              lambda: g_new == g_old - {"6854", "6924", "7823", "7827"} and "6423" in g_new and "6423" in g_old,
              lambda: g_old == g_old - {"6854", "6924", "7823", "7827"})
        # 合成資料夾：現名 -創、但以前在上櫃（非板）
        tmp = tempfile.mkdtemp(prefix="ugv2_")
        os.makedirs(os.path.join(tmp, "stocks")); os.makedirs(os.path.join(tmp, "meta"))
        pd.DataFrame([dict(stock_id="99001", name="測甲-創", market="twse", kind="stock", first_seen="2020-01-02", last_seen="2023-01-04")]).to_csv(
            os.path.join(tmp, "meta", "stocks.csv"), index=False)
        pd.DataFrame({"date": ["2020-01-02", "2020-01-03", "2023-01-03", "2023-01-04"], "stock_id": "99001",
                      "name": ["測甲", "測甲", "測甲-創", "測甲-創"], "market": ["tpex", "tpex", "twse", "twse"]}).to_csv(os.path.join(tmp, "stocks", "99001.csv"), index=False)
        st2 = pd.read_csv(os.path.join(tmp, "meta", "stocks.csv"), dtype=str)
        c2 = pd.DatetimeIndex(["2020-01-02", "2020-01-03", "2021-06-01", "2023-01-03", "2023-01-04"])
        check("合成：現名 -創、2020 在上櫃 ⇒ 留在靜態母體，2020 兩天（含其後停牌日）有效、2023 板期無效",
              lambda: "99001" in set(with_v2(True, lambda: _gate3_v2(st2, tmp))["stock_id"]) and
              list(with_v2(True, lambda: pit_valid("99001", c2, tmp))) == [True, True, True, False, False],
              lambda: "99001" in set(with_v2(False, lambda: gate3(st2))["stock_id"]))               # 舊口徑整檔剔 ⇒ 會紅
        sg = pd.DataFrame({"sid": ["6423", "6423", "2330"], "entry_pos": [pos("2025-03-04"), pos("2026-02-03"), pos("2025-03-04")]})
        check("filter_pit：6423 板期訊號剔、轉板後訊號留、一般股留",
              lambda: with_v2(True, lambda: filter_pit(sg, cal, data=snap))["entry_pos"].tolist() == [pos("2026-02-03"), pos("2025-03-04")],
              lambda: len(with_v2(False, lambda: filter_pit(sg, cal, data=snap))) == 2)
        shutil.rmtree(tmp, ignore_errors=True)
        check("GATE_V2 關 ⇒ pit_valid 全 True、filter_pit 原表照回（不作用）",
              lambda: with_v2(False, lambda: pit_valid("6423", cal, snap).all() and filter_pit(sg, cal, data=snap) is sg),
              lambda: with_v2(True, lambda: pit_valid("6423", cal, snap).all()))
    finally:
        GATE_V2 = old
    allok = all(o and r for _, o, r in res)
    print("⇒ G2 {}（{} 條，全過且每條反例都會紅）".format("✅ 全過" if allok else "⛔ 有不過", len(res)))
    return allok, res


def _broken_all_board(sid, cal, data):
    """反例用：故意把每一列都當成板內 ⇒ 一般股也全無效（驗「一般股不受影響」那條有鑑別力）。"""
    import numpy as np
    r = row_ok(sid, data)
    return np.zeros(len(cal), bool) if r is not None else np.ones(len(cal), bool)


if __name__ == "__main__":
    import sys as _sys
    if len(_sys.argv) > 1 and _sys.argv[1] == "v2":                # 裁定 seq293 §二 G2；不帶參數 ⇒ 舊自測照舊
        _ok, _ = _selftest_gate_v2(_sys.argv[2] if len(_sys.argv) > 2 else None)
        raise SystemExit(0 if _ok else 1)
    _selftest()
    _selftest_gate3()

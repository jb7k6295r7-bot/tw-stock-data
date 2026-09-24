# -*- coding: utf-8 -*-
"""資金費率讀取層（PREREGC2 §六①）——⭐ 報酬計算層的一部分，⛔ 不是共用引擎。

⛔⛔ 三條硬規矩（逐字出自 C2 v4 §六① 與資料庫線 1857／1936）：
  ① **逐列讀 funding_interval_hours**，⛔ 不可寫死 8（2023 年起部分交易對改 4／1 小時；
     ⭐ 實測 SOLUSDT 2022-11 就有 8／4／2 三種）
  ② last_funding_rate 是【小數】，⛔ 不是百分比（0.0001 ＝ 0.01%）
  ③ 月檔 absent（404）⇒ **該幣該月沒有永續合約** ⇒ ⛔ 不可當成費率 0
     ⇒ 要嘛拒絕該窗、要嘛把窗首切到第一個有檔的月；⛔ 不可靜默當 0
"""
from __future__ import annotations
import os
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
FIXDIR = os.path.join(HERE, "fixtures_c2")
COLS = ["calc_time", "funding_interval_hours", "last_funding_rate"]


class FundingAbsent(Exception):
    """該幣該月沒有月檔 ⇒ ⛔ 不是費率 0，是【沒有永續合約】。"""


def load_month(sym: str, y: int, m: int, root: str | None = None) -> pd.DataFrame:
    p = os.path.join(root or FIXDIR, "{}USDT-{:04d}-{:02d}.csv".format(sym, y, m))
    if not os.path.exists(p):
        raise FundingAbsent("{}USDT {:04d}-{:02d} 沒有月檔（⛔ 不可當費率 0）".format(sym, y, m))
    d = pd.read_csv(p)
    if list(d.columns) != COLS:
        raise SystemExit("⛔ 表頭不是逐字的 {} ⇒ 收到 {}".format(COLS, list(d.columns)))
    d["ts"] = pd.to_datetime(d["calc_time"], unit="ms", utc=True)
    return d


def settlements(sym: str, months: list[tuple[int, int]], root: str | None = None) -> pd.DataFrame:
    """把幾個月接起來。⛔ 任何一個月 absent 就丟 FundingAbsent（⛔ 不跳過、不補 0）。"""
    return pd.concat([load_month(sym, y, m, root) for y, m in months], ignore_index=True)


def cum_cost(d: pd.DataFrame) -> float:
    """累計資金費率成本 ＝ Σ last_funding_rate（⭐ 逐列，⛔ 不依間隔加權、⛔ 不補值）。"""
    return float(d["last_funding_rate"].sum())


def interval_mix(d: pd.DataFrame) -> dict:
    return {int(k): int(v) for k, v in d["funding_interval_hours"].value_counts().items()}


# ══ 全期資料（裁定線 20260924-2310 seq97 §三）════════════════════════════════
# 資料庫線 main：data/crypto_funding/<SYM>USDT.csv（逐月 zip 解開後串接，表頭逐字 COLS）
#               data/meta/crypto_funding_manifest.csv（一月一列：sym、月份、…、列數、間隔組成）
# ⭐ 回測線讀檔一律【釘 commit sha】（〈一百一十六〉）⇒ 經 git show 讀，⛔ 不讀 worktree 的 data/（分支快照比 main 舊）
# ⭐ 上面的 load_month／settlements／cum_cost 不動（fixture 與既有自測照舊）
import io as _io
import subprocess as _sp
import numpy as _np

FULL_REL = "data/crypto_funding/{}USDT.csv"
MANIFEST_REL = "data/meta/crypto_funding_manifest.csv"


def _git_show(repo: str, sha: str, rel: str) -> str:
    r = _sp.run(["git", "show", "{}:{}".format(sha, rel)], cwd=repo, capture_output=True, text=True)
    if r.returncode != 0:
        raise FileNotFoundError("⛔ git show {}:{} 失敗：{}".format(sha, rel, r.stderr.strip()[:200]))
    return r.stdout


def load_full(sym: str, sha: str | None = None, repo: str | None = None, path: str | None = None) -> pd.DataFrame:
    """讀一個幣的全期結算。⭐ 正式用法必給 sha（釘 commit）；path 只給自測用。"""
    if path is None:
        assert sha, "⛔ 讀全期資料必須釘 commit sha（〈一百一十六〉）"
        txt = _git_show(repo or os.path.expanduser("~/tw-stock-data"), sha, FULL_REL.format(sym))
        d = pd.read_csv(_io.StringIO(txt))
    else:
        d = pd.read_csv(path)
    if list(d.columns) != COLS:
        raise SystemExit("⛔ 表頭不是逐字的 {} ⇒ 收到 {}".format(COLS, list(d.columns)))
    d["ts"] = pd.to_datetime(d["calc_time"], unit="ms", utc=True)
    assert d["ts"].is_monotonic_increasing, "⛔ 結算時間不是遞增 ⇒ 串接順序錯了"
    assert not d["calc_time"].duplicated().any(), "⛔ 有重複的結算時點 ⇒ 月檔被接了兩次"
    return d.reset_index(drop=True)


def load_manifest(sha: str | None = None, repo: str | None = None, path: str | None = None) -> pd.DataFrame:
    if path is None:
        assert sha, "⛔ 清單也要釘 commit sha"
        m = pd.read_csv(_io.StringIO(_git_show(repo or os.path.expanduser("~/tw-stock-data"), sha, MANIFEST_REL)), dtype=str)
    else:
        m = pd.read_csv(path, dtype=str)
    # ⭐ 資料庫線 20260925-0306 交件的表頭（逐字）：sym,month,url,zip_sha256,content_sha256,rows,interval_mix,status
    #   ⇒ 對到本支原本用的中文欄名；status ∈ {ok, absent, error}（⛔ 三者不混、absent 不補 0）
    if {"month", "rows", "status"} <= set(m.columns):
        m = m.rename(columns={"month": "月份", "rows": "列數"})
    need = {"sym", "月份", "列數"}
    miss = need - set(m.columns)
    if miss:
        raise SystemExit("⛔ 清單缺欄 {}（實際欄：{}）⇒ 照資料庫線交件的欄名改這裡，⛔ 不猜".format(miss, list(m.columns)))
    if "status" in m.columns:
        bad = m[~m["status"].isin(["ok", "absent"])]
        assert bad.empty, "⛔ 清單有 status 非 ok／absent 的列：{}".format(bad[["sym", "月份", "status"]].head().values.tolist())
    return m


def month_of(d: pd.DataFrame, sym: str, y: int, mth: int, manifest: pd.DataFrame) -> pd.DataFrame:
    """取一個月。⭐ 清單沒有那一月 ⇒ FundingAbsent（⛔ 不是費率 0）；有 ⇒ 列數必須與清單逐字相符。"""
    key = "{:04d}-{:02d}".format(y, mth)
    row = manifest[(manifest["sym"].str.upper().str.replace("USDT", "") == sym.upper()) & (manifest["月份"] == key)]
    if "status" in row.columns:
        row = row[row["status"] == "ok"]               # absent ⇒ 當成沒有這一月（⛔ 不是費率 0）
    if row.empty:
        raise FundingAbsent("{}USDT {} 清單沒有這一月（⛔ 不可當費率 0）".format(sym, key))
    sub = d[(d["ts"].dt.year == y) & (d["ts"].dt.month == mth)]
    want = int(row["列數"].iloc[0])
    assert len(sub) == want, "⛔ {} {} 讀到 {} 列，清單寫 {} 列".format(sym, key, len(sub), want)
    return sub


def cashflow(d: pd.DataFrame, daily_close: pd.Series, qty=1.0) -> _np.ndarray:
    """C2 v6 §六⑤ 逐字：逐筆 ΔEquity_i ＝ −rate_i × 名目_i；名目_i ＝ 前一交易日收盤 × 數量。

    ⭐ 逐筆乘、再由呼叫端加總；⛔ 不提供「Σrate × 單一價」的捷徑（SOL 2022-11 會差 2.01 倍）
    ⭐ 前一交易日收盤 ＝ daily_close 往前移一列（加密日線是逐日）⇒ 理由是【不看未來】
    ⛔ 對不到前一日收盤 ⇒ 直接炸（⛔ 不用鄰日替代）
    """
    prev = daily_close.astype(float).shift(1)
    day = d["ts"].dt.tz_convert("UTC").dt.normalize().dt.tz_localize(None)
    px = day.map(prev)
    if px.isna().any():
        bad = day[px.isna()].iloc[:3].dt.date.tolist()
        raise KeyError("⛔ {} 筆結算對不到前一日收盤，例：{}".format(int(px.isna().sum()), bad))
    q = _np.broadcast_to(_np.asarray(qty, float), (len(d),))
    return -(d["last_funding_rate"].to_numpy(float) * px.to_numpy(float) * q)


def _selftest_full():
    """用既有三個月檔造一份「串接檔＋清單」，驗 seq97 §三 驗收②，並錨到本線 2205 的現金流。"""
    import tempfile
    tmp = tempfile.mkdtemp()
    parts = [pd.read_csv(os.path.join(FIXDIR, f)) for f in ("SOLUSDT-2020-09.csv", "SOLUSDT-2022-11.csv")]
    full = pd.concat(parts, ignore_index=True)
    fp = os.path.join(tmp, "SOLUSDT.csv"); full.to_csv(fp, index=False)
    man = pd.DataFrame([dict(sym="SOLUSDT", 月份="2020-09", 列數=str(len(parts[0]))),
                        dict(sym="SOLUSDT", 月份="2022-11", 列數=str(len(parts[1])))])
    mp = os.path.join(tmp, "manifest.csv"); man.to_csv(mp, index=False)

    d = load_full("SOL", path=fp); m = load_manifest(path=mp)
    nov = month_of(d, "SOL", 2022, 11, m)
    assert len(nov) == 165 and abs(cum_cost(nov) + 0.354915) < 5e-7 and interval_mix(nov) == {2: 99, 8: 64, 4: 2}
    print("✅ 驗收②：SOL 2022-11 ＝ 165 列、Σ −0.354915、間隔 {2:99, 8:64, 4:2}（串接檔＋清單路徑）")
    try:
        month_of(d, "SOL", 2022, 10, m)
        raise SystemExit("⛔ 清單沒有的月份竟然讀得到")
    except FundingAbsent:
        print("✅ 清單沒有 2022-10 ⇒ FundingAbsent（⛔ 不當費率 0）")
    bad = man.copy(); bad.loc[1, "列數"] = "164"
    try:
        month_of(d, "SOL", 2022, 11, bad)
        raise SystemExit("⛔ 列數與清單不符卻沒炸")
    except AssertionError:
        print("✅ 清單列數改 164 ⇒ 炸（⇒ 列數檢查會響）")

    px = pd.read_csv(os.path.join(os.path.dirname(HERE), "data", "crypto", "SOL.csv"), parse_dates=["date"]).set_index("date")["close"]
    cf = cashflow(nov, px, qty=1.0).sum()
    assert abs(cf - 5.679914) < 5e-6, "⛔ 現金流沒對上本線 2205 的 5.679914：{}".format(cf)
    wrong = -cum_cost(nov) * float(px.loc["2022-11"].iloc[0])
    assert abs(wrong / cf - 2.01) < 0.01, "⛔ 反例（Σrate×月初收盤）應是 2.01 倍"
    print("✅ 逐筆現金流（持有 1 顆）＝ {:.6f} USDT ＝ 本線 2205 的數；反例 Σrate×月初收盤 ＝ {:.4f}（{:.2f} 倍）⇒ 分得出".format(
        cf, wrong, wrong / cf))
    try:
        cashflow(nov, px.loc[:"2022-11-10"], qty=1.0)
        raise SystemExit("⛔ 價缺了卻沒炸")
    except KeyError:
        print("✅ 前一日收盤缺 ⇒ 炸（⛔ 不用鄰日替代）")


if __name__ == "__main__":
    _selftest_full()

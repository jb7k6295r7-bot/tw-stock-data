# -*- coding: utf-8 -*-
"""C5 永續價複核（裁定線 seq124 §三、seq125 §三；只決定措辭，⛔ 不改判定、不計 N）——資料到位前先備好。

閘門（⛔ 不綠就停）：
 G1 回歸：不給永續價 ⇒ 六幣 × MMR 三格的年化與交件 resultsc5/summary.json 逐位相同
 G2 fixture：永續價 ＝ 現貨價 × 1.01（固定比例基差）⇒ 與現貨版逐期相同（對沖比例不變）；基差隨時間變 ⇒ 必須不同
複核（資料到位後）：data/crypto_perp/<SYM>USDT.csv 釘資料庫線交件的 commit（用法：--sha <commit>）
   表頭（資料庫 0306 §四）open_time,open,high,low,close,volume,close_time,quote_volume,count,taker_buy_volume,taker_buy_quote_volume,ignore
   先驗三項：① 下限（BTC 應 2020-01 起）② 逐日無缺 ③ UTC 00:00 日界（open_time mod 86400000 ＝ 0）
   窗＝max(C5 主格窗首, 永續第一天) ～ 2026-08-31；同窗報【永續版】與【現貨版】並排（兩版差只來自價格源）；永續版報 N＝31 CI（B＝62,000）
"""
import os, sys, io, json, subprocess
import numpy as np, pandas as pd
sys.path.insert(0, os.path.expanduser("~/tw-p17")); os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import researchc1 as C, researchc2 as C2, researchc5 as C5, funding as F

HDR = ["open_time", "open", "high", "low", "close", "volume", "close_time", "quote_volume", "count", "taker_buy_volume", "taker_buy_quote_volume", "ignore"]
man = F.load_manifest(path=os.path.join(C2.ROOT, "data", "meta", "crypto_funding_manifest.csv"))
R = {r["coin"]: r for r in json.load(open("backtest/resultsc5/summary.json", encoding="utf-8"))}


def window(sym):
    d = C2.load_px(sym); da = d["date"].to_numpy()
    i0 = int(np.flatnonzero(da == R[sym]["窗首（建倉日）"])[0]); i1 = int(np.flatnonzero(da == R[sym]["窗尾"])[0])
    return d.iloc[i0:i1 + 1].reset_index(drop=True)


def gates():
    for s in C5.COINS:
        w = window(s); fbd, _ = C2.fund_days(s, w["date"].to_numpy(), man)
        for mmr in C5.MMRS:
            r, liq, _, _ = C5.engine(w["close"].to_numpy(float), w["high"].to_numpy(float), fbd, mmr)
            assert C.cagr(r) == R[s]["MMR"][f"{mmr:.1%}"]["年化"], ("⛔ G1 回歸不符", s, mmr)
    w = window("BTC"); fbd, _ = C2.fund_days("BTC", w["date"].to_numpy(), man)
    c, h = w["close"].to_numpy(float), w["high"].to_numpy(float)
    r0, _, _, _ = C5.engine(c, h, fbd, 0.02)
    r1, _, _, _ = C5.engine(c, h, fbd, 0.02, pclose=c * 1.01, phigh=h * 1.01)
    assert np.allclose(r0, r1, atol=1e-12), "⛔ G2 固定比例基差應與現貨版相同"
    wave = 1 + 0.01 * np.sin(np.arange(len(c)) / 30)
    r2, _, _, _ = C5.engine(c, h, fbd, 0.02, pclose=c * wave, phigh=h * wave)
    assert not np.allclose(r0, r2, atol=1e-9), "⛔ G2 變動基差卻與現貨版相同 ⇒ 永續價沒進到損益"
    print("✅ G1 回歸：六幣 × MMR 三格年化與交件逐位相同｜G2 固定比例基差 ⇒ 相同、變動基差 ⇒ 不同")


def load_perp(sym, sha):
    r = subprocess.run(["git", "show", f"{sha}:data/crypto_perp/{sym}USDT.csv"], cwd=os.path.expanduser("~/tw-stock-data"), capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit(f"⛔ 讀不到 {sha}:data/crypto_perp/{sym}USDT.csv（{r.stderr.strip()[:120]}）⇒ 永續日 K 尚未落檔，複核不能跑")
    d = pd.read_csv(io.StringIO(r.stdout))
    assert list(d.columns) == HDR, f"⛔ 表頭不是交件寫的 {HDR}：{list(d.columns)}"
    assert (d["open_time"] % 86_400_000 == 0).all(), "⛔ 日界不是 UTC 00:00"
    d["date"] = pd.to_datetime(d["open_time"], unit="ms", utc=True).dt.strftime("%Y-%m-%d")
    d = d.drop_duplicates("date").sort_values("date").reset_index(drop=True)
    gap = (pd.to_datetime(d["date"].iloc[-1]) - pd.to_datetime(d["date"].iloc[0])).days + 1
    assert gap == len(d), f"⛔ {sym} 永續日 K 有缺口"
    return d


def recheck(sha):
    out = {"資料commit": sha}
    for s in ("BTC", "ETH"):
        w = window(s); p = load_perp(s, sha)
        start = max(w["date"].iloc[0], p["date"].iloc[0])
        w = w[w["date"] >= start].reset_index(drop=True)
        pm = p.set_index("date").reindex(w["date"])
        assert pm["close"].notna().all(), "⛔ 窗內永續日 K 有缺"
        fbd, _ = C2.fund_days(s, w["date"].to_numpy(), man)
        c, h = w["close"].to_numpy(float), w["high"].to_numpy(float)
        rs, ls, _, _ = C5.engine(c, h, fbd, 0.02)
        rp, lp, _, _ = C5.engine(c, h, fbd, 0.02, pclose=pm["close"].to_numpy(float), phigh=pm["high"].to_numpy(float))
        rec = {"窗": [start, w["date"].iloc[-1]], "永續第一天": p["date"].iloc[0],
               "現貨版（同窗）": {"年化": C.cagr(rs), "回落": C.mdd(rs), "強平": ls is not None},
               "永續版": {"年化": C.cagr(rp), "回落": C.mdd(rp), "強平": lp is not None}}
        if lp is None:
            L = C.politis_white_block(rp); a = 0.05 / 31
            smp = C5.boot_cagr(rp, L, np.random.default_rng(C.SEED), 62_000)
            rec["永續版"].update({"L": L, "N31 CI": [float(np.percentile(smp, 100 * a / 2)), float(np.percentile(smp, 100 * (1 - a / 2)))]})
        out[s] = rec
        print(s, json.dumps(rec, ensure_ascii=False, default=float))
    json.dump(out, open("backtest/resultsc5/perp_recheck.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)


if __name__ == "__main__":
    gates()
    if "--sha" in sys.argv:
        recheck(sys.argv[sys.argv.index("--sha") + 1])
    else:
        print("⏳ 未給 --sha（永續日 K 尚未落檔）⇒ 只跑閘門")

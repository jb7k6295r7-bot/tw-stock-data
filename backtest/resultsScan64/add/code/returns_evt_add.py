# -*- coding: utf-8 -*-
"""scanadd：事件型補格報酬（目前只有 S59 興櫃轉上櫃，讀法 B，裁定 seq531）。
⛔ 不另寫事件算法：事件報酬、母體基準、月分群、自助法、假訊號、判語分類全部直接執行 ../../code/returns.py 的原始碼
（seg_of、cbb_idx、boot、RH／BENCH 迴圈、load_events、event_excess、summarize_events、shuffle_events、verdict_events、label_desc），
returns.py 本身一字不改（64 格不受影響）。returns.py 在 module 層會讀 64 格自己的 cache／factors 並用真價格算 RH，
所以不 import 它，改成把上述段落的原始碼抽出來、在本檔的命名空間執行（本檔先備好它們用到的全域：價格、母體、門檻）。
本檔自己的只有：讀面板與母體（同 add/code/returns_add.py）、dry／fixture 換價格、門檻常數、輸出欄位。
門檻（seq526／531）：判語區間＝3 個持有期各 0.05/207（returns.py 的 loEV／hiEV）；描述＝0.05/69（returns.py 的 loB／hiB）；95% 描述。
用法（add/code/run.sh）：returns_evt_add.py dry|fixture|real [S59]
  dry ⇒ 報酬全 0，輸出 ~/scanadd/dry/；fixture ⇒ 隨機漫步假價格（非真報酬），輸出 ~/scanadd/fixture/；real ⇒ 正式跑（主線自己跑），輸出 ~/scanadd/。"""
import os, sys, time, ast, hashlib, json
import numpy as np, pandas as pd
import snap
from backtest import data as D
D = snap.fix()

MODE = sys.argv[1] if len(sys.argv) > 1 else "dry"
assert MODE in ("dry", "real", "fixture")
CODES = sys.argv[2:] or ["S59"]
assert CODES == ["S59"], CODES
t0 = time.time()
BASE = snap.BASE
FAC = os.path.join(BASE, "factors"); CACHE = os.path.join(BASE, "cache")
OUT = BASE if MODE == "real" else os.path.join(BASE, MODE)
OUT_M = os.path.join(OUT, "monthly"); os.makedirs(OUT_M, exist_ok=True)

# ───── returns.py 用到的全域（值同 64 格；門檻換成 seq526／531 的 69 格版） ─────
EXP = ("2017-03", "2021-12"); CON = ("2022-01", "2026-08")
MIN_VAL, MIN_TOP_BIN, MIN_GROUPS = 50, 5, 24
NCELL = 69
A95 = 0.05
AB = 0.05 / NCELL                 # 描述：各持有期 0.05/69（returns.py 的 loB／hiB 欄）
AEV = 0.05 / (NCELL * 3)          # 判語區間：0.05/207（returns.py 的 loEV／hiEV 欄）
B, BLOCK, SEED = 4000, 6, 5
HOLDS = (20, 60, 120)
DATA_END = pd.Timestamp("2026-11-27")

# ───── 面板與母體（同 returns_add.py） ─────
P = np.load(os.path.join(CACHE, "panel.npz"))
cal = pd.DatetimeIndex(pd.to_datetime(P["cal"])); sids = [str(s) for s in P["sids"]]
VALID = P["VALID"] == 1
C = P["C"].astype(float); C[~VALID] = np.nan
if MODE == "dry":
    C = np.where(np.isfinite(C), 1.0, np.nan)          # ⛔ 乾跑：報酬全 0（保留有效／缺值樣態）
if MODE == "fixture":                                   # 合成 fixture：隨機漫步假價格（非真報酬），同 returns_add.py
    _r = np.random.default_rng(123).normal(0, 0.02, C.shape)
    C = np.where(np.isfinite(C), np.exp(np.cumsum(_r, 0)), np.nan)
BAD = np.nan_to_num(P["BAD"]) > 0
T, N = C.shape
Cff = pd.DataFrame(C).ffill().to_numpy()
CB = np.vstack([np.zeros((1, N)), np.cumsum(BAD, 0)])
DATA_LAST = cal[np.flatnonzero(VALID.any(1))[-1]]
assert DATA_LAST == cal[-1] == DATA_END, (DATA_LAST, cal[-1])   # 出場位置 ≥T（超過 2026-11-27）⇒ returns.py 的 RH 迴圈 break、不計

U_df = pd.read_parquet(os.path.join(FAC, "universe.parquet"))
me_dates = pd.DatetimeIndex(pd.to_datetime(U_df.index))
assert list(U_df.columns) == sids
U = U_df.to_numpy(bool)
NM = len(me_dates)

# ───── 執行 returns.py 的原始碼段落（唯一實作） ─────
RET = os.path.join(os.path.dirname(os.path.abspath(snap.__file__)), "returns.py")
_src = open(RET, encoding="utf-8").read()
RET_SHA = hashlib.sha256(_src.encode("utf-8")).hexdigest()


def _section(a, b):
    i = _src.index(a); j = _src.index(b, i)
    assert _src.count(a) == 1 and _src.count(b) == 1, (a, b)
    return _src[i:j]


_tree = ast.parse(_src)
_FUN = ("seg_of", "verdict_events", "label_desc")
_fn = [n for n in _tree.body if isinstance(n, ast.FunctionDef) and n.name in _FUN]
assert sorted(n.name for n in _fn) == sorted(_FUN)
exec(compile("\n\n".join(ast.get_source_segment(_src, n) for n in _fn), RET + "[seg_of,verdict_events,label_desc]", "exec"), globals())
exec(compile(_section("# ───────── 自助法 ─────────", "# ───────── 橫斷面 ─────────"), RET + "[自助法]", "exec"), globals())
exec(compile(_section("# ───────── 事件 ─────────", "# ───────── 判語 ─────────"), RET + "[事件]", "exec"), globals())
for _f in (seg_of, cbb_idx, boot, load_events, event_excess, summarize_events, shuffle_events, verdict_events, label_desc):
    assert _f.__code__.co_filename.startswith(RET), _f
if MODE == "dry":
    assert all(np.nanmax(np.abs(RH[h])) == 0 for h in HOLDS), "乾跑報酬不是 0"

NOTE3 = "名單為推定；讀法 B（同 S58 實作，不是登錄字面）；S59 的事件全部包含在 S58 裡（佔 S58 約 4 成）"


def fmt(x, k=5):
    return round(float(x), k) if x is not None and np.isfinite(x) else np.nan


def main():
    snap.check()
    rows, shuf = [], []
    code, name = "S59", "興櫃轉上櫃（讀法 B，seq531）"
    e = load_events(code)
    X = event_excess(e)
    r = summarize_events(e, X)
    rng = np.random.default_rng(SEED)
    js = shuffle_events(e, rng)
    Xs = event_excess(e, js)
    rs = summarize_events(e, Xs)
    vd, why = verdict_events(r); vs, _ = verdict_events(rs)
    labs = "；".join(f"{h}日:" + label_desc(r["探索"][h], r["確認"][h], r["確認"][h]["n"]) for h in HOLDS)
    ev = pd.DataFrame({"stock_id": e.stock_id, "event": e.event_date, "entry": e.entry_date, "month": e.month, "seg": e.seg, "kind": e.kind,
                       **{f"x{h}": X[h] for h in HOLDS}, **{f"shuf{h}": Xs[h] for h in HOLDS}, "shuf_stock": np.array(sids)[js]})
    ev.to_csv(os.path.join(OUT_M, f"{code}_events_excess.csv.gz"), index=False, compression="gzip")
    base = {"S號": code, "因子": name, "類別": "規模與事件", "型別": "事件", "方向": "事件"}
    for sg in ("探索", "確認"):
        row = {**base, "段": sg, "可用月或事件群": "／".join(str(r[sg][h]["n"]) for h in HOLDS)}
        for h in HOLDS:
            z, zs = r[sg][h], rs[sg][h]
            row.update({f"事件{h}日_超額": fmt(z["mean"]), f"事件{h}日_95%下": fmt(z["lo95"]), f"事件{h}日_95%上": fmt(z["hi95"]),
                        f"事件{h}日_Bonf下(0.05/69,描述)": fmt(z["loB"]), f"事件{h}日_Bonf上(0.05/69,描述)": fmt(z["hiB"]),
                        f"事件{h}日_判語區間下(0.05/207)": fmt(z["loEV"]), f"事件{h}日_判語區間上(0.05/207)": fmt(z["hiEV"]),
                        f"事件{h}日_群數": z["n"], f"事件{h}日_事件數": z["n_ev"], f"事件{h}日_事件加權平均": fmt(z["ev_mean"]),
                        f"假訊號{h}日_超額": fmt(zs["mean"]), f"假訊號{h}日_95%下": fmt(zs["lo95"]), f"假訊號{h}日_95%上": fmt(zs["hi95"]),
                        f"假訊號{h}日_判語區間下(0.05/207)": fmt(zs["loEV"]), f"假訊號{h}日_判語區間上(0.05/207)": fmt(zs["hiEV"]),
                        f"假訊號{h}日_群數": zs["n"]})
        con = sg == "確認"
        row.update({"描述標籤(0053,95%)": labs if con else "",
                    "依門檻落點(確認段,判語區間0.05/207,群數<24不判)": (vd + (f"（{why}）" if why else "")) if con else "",
                    "假訊號落點(0.05/207)": vs if con else "",
                    "判語(裁定)": "",
                    "判語固定附註(最高到暫定)": NOTE3 if con else ""})
        rows.append(row)
        for h in HOLDS:
            zs = rs[sg][h]
            shuf.append(dict(code=code, typ="事件", seg=sg, h=h, mean=zs["mean"], lo95=zs["lo95"], hi95=zs["hi95"], loB=zs["loB"], hiB=zs["hiB"],
                             loEV=zs["loEV"], hiEV=zs["hiEV"], n=zs["n"]))
    df = pd.DataFrame(rows)
    df["門檻依據"] = "seq526／531：判語 0.05/207（=0.05/(69×3)）；0.05/69 只描述"
    df["程式"] = f"returns.py sha256 {RET_SHA[:16]}…（原始碼段落原樣執行）；資料 {snap.SHA}；MODE={MODE}"
    df.to_csv(os.path.join(OUT, f"result_{code}.csv"), index=False, encoding="utf-8-sig")
    pd.DataFrame(shuf).to_csv(os.path.join(OUT_M, f"{code}_shuffle_cells.csv"), index=False)
    num = df.select_dtypes("number")
    assert not np.isinf(num.to_numpy()).any(), "有 inf"
    # 驗收：群數對 s59_freq.json 的 B
    fj = json.load(open(os.path.join(BASE, "s59", "s59_freq.json")))["B"]
    chk = {f"{sg}{h}": (r[sg][h]["n"], fj[f"群數{sg}_{h}日"]) for sg in ("探索", "確認") for h in HOLDS}
    print("群數（本程式, s59_freq.json）", chk)
    if MODE != "real":
        print("群數一致" if all(a == b for a, b in chk.values()) else "⚠ 群數不一致")
    if MODE == "dry":
        means = [r[sg][h][k] for sg in ("探索", "確認") for h in HOLDS for k in ("mean", "ev_mean")] + \
                [rs[sg][h][k] for sg in ("探索", "確認") for h in HOLDS for k in ("mean", "ev_mean")]
        assert all(m == 0 for m in means if np.isfinite(m)), "乾跑平均超額不是 0"
        print("乾跑：平均超額全 0")
    print(df.T.to_string() if MODE != "real" else df[["段", "可用月或事件群"]].to_string())
    print("MODE", MODE, "DATA_LAST", DATA_LAST.date(), "SHA", snap.SHA, "returns.py", RET_SHA, f"elapsed {time.time() - t0:.0f}s")
    snap.check()


if __name__ == "__main__":
    main()

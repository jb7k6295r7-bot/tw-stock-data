"""PREREGP1 回歸基線：用【改動前】的 research11.simulate_mtm 跑一次，把逐種子的 cagr/mdd/slot/trades 存起來。
改動引擎之後 researchp1.py --regress 要逐種子逐格重現這份（bit-for-bit）。"""
import os, sys, time
import numpy as np, pandas as pd
sys.path.insert(0, "/home/user/tw-stock-data")
from backtest import research11 as R, data as D

OUT = "/home/user/tw-stock-data/backtest/resultsp1/regress"
os.makedirs(OUT, exist_ok=True)
t0 = time.time()
cal = D.load_calendar(); ncal = len(cal)
# ① S 集合（研究十一主格 24,286 筆）。⚠ research11 只存了 closes.npz、沒有 opens.npz ⇒ 兩個都用 D.load_stock 重建（今天的 data/adj），
#   與 research13 同法；研究十一那 12 格只能做「容忍價格改版」的對照，逐種子精確重現的對象是本檔自己存的基線。
S = pd.read_csv("/home/user/tw-stock-data/backtest/results11/signals.csv.gz", dtype={"sid": str})
AND = pd.read_csv("/home/user/tw-stock-data/backtest/results13b/and_signals.csv.gz", dtype={"sid": str})
uni = D.load_universe().set_index("stock_id")["market"]
closes, opens = {}, {}
for sid in sorted(set(S["sid"]) | set(AND["sid"])):
    st = D.load_stock(sid, uni.get(sid, "twse"), cal)
    if st is None:
        continue
    closes[sid] = pd.Series(st.df["close"].to_numpy()).ffill().to_numpy(np.float32); opens[sid] = st.df["open"].to_numpy(np.float32)
np.savez_compressed(os.path.join(OUT, "closes.npz"), **closes); np.savez_compressed(os.path.join(OUT, "opens.npz"), **opens)
print(f"closes/opens {len(closes)} 檔 {time.time()-t0:.0f}s", flush=True)
res = {}
for N in (5, 10, 20):
    for rule in ("H20", "H60", "H120", "LD"):
        st = [R.simulate_mtm(S, rule, N, np.random.default_rng(3000 + r), closes, opens, ncal) for r in range(200)]
        for key in ("cagr", "mdd", "slot_use", "trades"):
            res[f"S_{N}_{rule}_{key}"] = np.array([x[key] for x in st], float)
        print(f"S N={N} {rule}: cagr med {np.median(res[f'S_{N}_{rule}_cagr'])*100:+.1f}% mdd {np.median(res[f'S_{N}_{rule}_mdd'])*100:.1f}% slot {np.median(res[f'S_{N}_{rule}_slot_use'])*100:.0f}% trades {np.median(res[f'S_{N}_{rule}_trades']):.0f}  {time.time()-t0:.0f}s", flush=True)
np.savez_compressed(os.path.join(OUT, "baseline_S.npz"), **res)
# ② AND 集合（results13b 2,199 筆），同一份 closes/opens
closes2, opens2 = closes, opens
res2 = {}
for N in (10, 20, 30, 40):
    for rule in ("H60", "H120", "LD"):
        st = [R.simulate_mtm(AND, rule, N, np.random.default_rng(1000 + r), closes2, opens2, ncal) for r in range(200)]
        for key in ("cagr", "mdd", "slot_use", "trades"):
            res2[f"AND_{N}_{rule}_{key}"] = np.array([x[key] for x in st], float)
        print(f"AND N={N} {rule}: cagr med {np.median(res2[f'AND_{N}_{rule}_cagr'])*100:+.1f}% mdd {np.median(res2[f'AND_{N}_{rule}_mdd'])*100:.1f}%  {time.time()-t0:.0f}s", flush=True)
np.savez_compressed(os.path.join(OUT, "baseline_AND.npz"), **res2)
print(f"完成 {time.time()-t0:.0f}s")

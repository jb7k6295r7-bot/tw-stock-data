# K33 更正：新舊比對（其餘 95 變體逐欄同、K33 兩格新舊、族結論）⇒ resultsPatAll_K33fix/compare.json、K33_CHANGE.md
import json, os
import pandas as pd
os.chdir(os.path.expanduser("~/tw-p17"))
B = "backtest/resultsPatAll_K33fix"
o = pd.read_csv("backtest/resultsPatAll/body/cells.csv", encoding="utf-8-sig", dtype={"vid": str})
n = pd.read_csv(f"{B}/body/cells.csv", encoding="utf-8-sig", dtype={"vid": str})
so = json.load(open("backtest/resultsPatAll/body/summary.json", encoding="utf-8")); sn = json.load(open(f"{B}/body/summary.json", encoding="utf-8"))
cols = [c for c in o.columns if c in n.columns and c not in ("句子", "vid", "H")]
oo = o[o.vid != "K33"].set_index(["vid", "H"])[cols].astype(object).where(lambda x: x.notna(), "").astype(str); nn = n[n.vid != "K33"].set_index(["vid", "H"])[cols].astype(object).where(lambda x: x.notna(), "").astype(str)
ndiff = int((oo != nn.loc[oo.index]).to_numpy().sum())
keep = ["H", "原始", "保留", "n", "dX̄", "中位", "勝率", "lo", "hi", "bonf_lo", "bonf_hi", "n_eff", "出口", "結果", "假訊號_新預設_x2", "假訊號_新預設_x3"]
k_o = o[o.vid == "K33"][keep].to_dict("records"); k_n = n[n.vid == "K33"][keep].to_dict("records")
fo, fn = so["族"], sn["族"]
res = {"其餘95變體×3H 逐欄不同格數（空值視為相同）": ndiff, "K33_舊（第一根白K）": k_o, "K33_新（第一根黑K）": k_n,
       "標籤翻轉（判定格 H20／H60）": {str(a["H"]): [a["結果"], b["結果"]] for a, b in zip(k_o, k_n) if a["H"] in (20, 60)},
       "族": {"a 舊→新": [fo["a_d方向過關"], fn["a_d方向過關"]], "b 舊→新": [fo["b_反方向過關"], fn["b_反方向過關"]],
             "假訊號新預設最大 舊→新": [fo["假訊號_新預設_最大"], fn["假訊號_新預設_最大"]], "與運氣分不開 舊→新": [fo["與運氣分不開"], fn["與運氣分不開"]],
             "族結論句_新": fn["族結論句"]}}
json.dump(res, open(f"{B}/compare.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
print(json.dumps(res, ensure_ascii=False, indent=1, default=str))

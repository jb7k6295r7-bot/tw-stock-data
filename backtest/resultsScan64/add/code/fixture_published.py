# -*- coding: utf-8 -*-
"""合成 fixture：驗 published 可用日（不含任何報酬）。"""
import numpy as np, pandas as pd
import insider as I

rows = [
    # stock, data_ym, published, value
    ("1111", "2020-01", "2020-02-20", 1.0),
    ("1111", "2020-02", "2020-04-01", 99.0),   # published 晚於量測日 2020-03-31 ⇒ 不可用，應回到 2020-01
    ("2222", "2020-01", "2020-02-20", 5.0),
    ("2222", "2020-02", "2020-03-20", 6.0),     # 可用
    ("3333", "2020-02", "2020-03-31", 7.0),     # published＝量測日 ⇒ 可用（≤）
    ("3333", "2020-01", "2020-03-31", 3.0),
    ("4444", "2019-12", "2020-01-20", 8.0),     # 太舊（< 2020-03 − 2）⇒ 空
    ("5555", "2020-03", "2020-03-15", 9.0),     # data_ym＝量測月（published 早於量測日）⇒ 可用
    ("5555", "2020-02", "2020-04-10", 4.0),     # 前一期 published 晚於量測日 ⇒ prev 應為空
]
x = pd.DataFrame(rows, columns=["stock_id", "data_ym", "published", "v"])
x, info = I.prep(x, ["v"])
t = pd.DatetimeIndex(["2020-03-31", "2020-04-30"])
sids = ["1111", "2222", "3333", "4444", "5555"]
A = I.asof(x, ["v"], t, sids)
v, p = A["val"]["v"], A["prev"]["v"]
print("val 2020-03-31", v[0], "prev", p[0])
print("val 2020-04-30", v[1], "prev", p[1])
exp_v0 = [1.0, 6.0, 7.0, np.nan, 9.0]; exp_p0 = [np.nan, 5.0, 3.0, np.nan, np.nan]
exp_v1 = [99.0, 6.0, 7.0, np.nan, 9.0]; exp_p1 = [1.0, 5.0, 3.0, np.nan, 4.0]
for a, b, nm in ((v[0], exp_v0, "v0"), (p[0], exp_p0, "p0"), (v[1], exp_v1, "v1"), (p[1], exp_p1, "p1")):
    assert np.allclose(a, b, equal_nan=True), (nm, a, b)
# 1111 在 2020-03-31：prev 為空，因為選到的是 2020-01（2019-12 不存在）
print("FIXTURE OK：published 晚於量測日的一期（1111 2020-02、5555 2020-02）在 2020-03-31 都沒被用到；＝量測日的可用；太舊的為空")

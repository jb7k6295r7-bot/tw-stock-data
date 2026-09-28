# 共用引擎：held_map 開關閘門（PREREG營量出場 seq1 甲件）

回測線，2026-09-28（台北）。

- `research11.simulate_mtm(..., held_map=None)`：預設關。開時 sig 的 sid 是逐筆合成價格序列的鍵，「已持有同一檔」改用 held_map[sid]（底層代號）判。
- 引擎內改 4 處（`# _HELDMAP`）：出場 held.discard、log 的 c 記錄、候選排除、進場 held.add；另加 1 處互斥檢查（與 nx_pool／trim_proceeds／stop_proceeds／cap_fn／tradable 不同開）。

| 閘 | 結果 |
|---|---|
| E0 fixture | {'開：A#12 因 A 已持有被擋（trades 2）': True, '關：A#12 當不同檔進場（trades 3）': True, '恆等 held_map ＝ 預設（equity 逐位元）': True, '與 cap_fn 同開 ⇒ ValueError': True} |
| E1 開關關 ＝ HEAD 引擎（營量、營飆各 5 顆：equity＋回傳 dict） | {'比對': 10, '不同': 0} |
| E2 開關開＋合成鍵（原序列）＝ 營量 v1（eq_sha 不同顆數） | 0 |
| G1 營量 v1 主 200 顆 ＝ resultsT1fix c13 t1（eq_sha 不同顆數） | 0 |
| G1 營飆 v1 主 200 顆 ＝ resultsT1fix c1 t1（eq_sha 不同顆數） | 0 |

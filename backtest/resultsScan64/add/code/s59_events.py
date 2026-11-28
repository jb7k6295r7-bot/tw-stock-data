# -*- coding: utf-8 -*-
"""scanadd：S59 興櫃轉上櫃 讀法 B（裁定 seq531）事件表 ⇒ ~/scanadd/factors/S59_events.csv（factors.save_events 原欄位）。
來源：~/scanadd/s59/s59_events_both.csv（add/code/s59_freq.py 產生；名單 ~/s59/emerging_to_otc.csv sha 00101a75…aac84）。
B＝同 S58 實作：第一次進入當年母體的月底（距上櫃首日 ≤550 天）＝event_date；進場＝下一交易日＝entry_date。⛔ 不算任何報酬。"""
import os, hashlib
import pandas as pd
import snap
import factors as F            # 只用 save_events（唯一實作）；import 時 factors 會讀 ~/scanadd/cache/panel.npz
D = snap.fix(); snap.check()
LIST = os.path.expanduser("~/s59/emerging_to_otc.csv")
assert hashlib.sha256(open(LIST, "rb").read()).hexdigest() == "00101a7581612213fc01988988416be3324f09d6f8abd83c7270f424142aac84"
ev = pd.read_csv(os.path.join(snap.BASE, "s59", "s59_events_both.csv"), dtype=str)
b = ev[ev.B_entry.notna() & (ev.B_entry != "")]
cal = set(F.cal.strftime("%Y-%m-%d"))
assert b.B_entry.isin(cal).all() and b.B_form.isin(cal).all()
rows = [(s, f, e, "B:同S58實作(seq531)") for s, f, e in zip(b.stock_id, b.B_form, b.B_entry)]
F.save_events("S59", rows)
print("S59 B events", len(rows), "→", os.path.join(F.FAC, "S59_events.csv"))
snap.check()

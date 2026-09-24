# -*- coding: utf-8 -*-
"""把 amt 版訂正段【逐字】追加到 backtest/results3_amt/summary.md 檔尾。
⇐ 裁定線 20260924-1934（seq69）過目通過；市場情報分析線 1932 交件
⛔ 本線【不手打任何一個字】：整份讀進來原樣貼上；⭐ 先驗 sha256[:16]（整檔原始位元組），對不上就不動。
"""
import os, sys, hashlib, io
sys.path.insert(0, os.path.expanduser("~/tw-p17")); os.chdir(os.path.expanduser("~/tw-p17"))

SRC = "/mnt/c/SynologyDrive/跨線信箱/訂正段全文-results3_amt五千萬母體_市場情報分析線_shaef3dd1e2d4ab60fa-11105B-20260924-1931.md"
WANT, WANT_B = "ef3dd1e2d4ab60fa", 11105
DST = "backtest/results3_amt/summary.md"
MARK = "訂正段（市場情報分析線"

raw = open(SRC, "rb").read()
got, nb = hashlib.sha256(raw).hexdigest()[:16], len(raw)
print("來源 sha16 {} ({:,} B)｜宣稱 {} ({:,} B) ⇒ {}".format(
    got, nb, WANT, WANT_B, "✅ 相符" if (got == WANT and nb == WANT_B) else "⛔ 不符"))
if got != WANT or nb != WANT_B:
    raise SystemExit("⛔ sha 或位元組不符 ⇒ 不動 {}".format(DST))
if not os.path.exists(DST):
    raise SystemExit("⛔ 目標不存在：{}".format(DST))
print("⭐ 目錄內容：", sorted(os.listdir("backtest/results3_amt")))

cur = io.open(DST, encoding="utf-8").read()
if MARK in cur:
    raise SystemExit("⚠ 已經追加過（檔中已有「{}」）⇒ 不重複接".format(MARK))
body = raw.decode("utf-8")
block = "\n\n---\n\n" + body.rstrip("\n") + "\n"
io.open(DST, "a", encoding="utf-8", newline="").write(block)
out = open(DST, "rb").read()
print("\n✅ 已逐字追加 ⇒ {}".format(DST))
print("   新 sha256[:16] ＝ {}｜{:,} B（追加前 {:,} B）".format(
    hashlib.sha256(out).hexdigest()[:16], len(out), len(cur.encode())))

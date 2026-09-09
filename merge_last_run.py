#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把兩份 `_last_run.md` **逐區塊**合併，每個區塊留「最後執行」較新的那一份。

    python3 merge_last_run.py 本趟.md 對方.md > 合併.md

## 為什麼不能像別的報告檔那樣「整份取一邊」

`_db_status.md`、各支 `_*probe.txt` 是**每趟從當下 repo 資料整份重生**的，
誰贏都一樣。⛔ `_last_run.md` **不是**——`runlog` 只覆蓋自己那一個區塊，
所以這一份是**跨 workflow 累積**的：daily 寫 fetch／adjust，
capital 寫 capital，suspend 寫 suspend……

整份取一邊 ⇒ 另一邊的區塊被回退成舊的。
⚠ 最貴的形狀：**另一支剛報的 ✗ 被安靜換成上一輪的 ✓**。
檔案在、格式對、區塊數一樣，只是某一塊的狀態悄悄變回綠的。

## 判準

只看區塊自己宣告的「最後執行」時間，⛔ 不看檔案 mtime、不看誰在 rebase 的哪一側。
時間解析不出來的區塊一律**保留**（寧可留兩份也不要丟掉一份）；
兩邊都有而時間相同時取本趟那一份。
"""
import io
import re
import sys

HEAD_RE = re.compile(r"^## (.+?)(?:\s|　)*(?:✓|✗|$)", re.M)
TS_RE = re.compile(r"^最後執行：([0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9:]{8}[+\-][0-9:]{5})", re.M)


def split_blocks(txt):
    """回傳 (前言, [(區塊名, 區塊全文), ...])。區塊順序保留。"""
    pos = [m.start() for m in re.finditer(r"^## ", txt, re.M)]
    if not pos:
        return txt, []
    out = []
    for i, p in enumerate(pos):
        end = pos[i + 1] if i + 1 < len(pos) else len(txt)
        body = txt[p:end]
        m = HEAD_RE.match(body)
        name = m.group(1).strip() if m else body.splitlines()[0][3:].strip()
        out.append((name, body))
    return txt[:pos[0]], out


def ts(body):
    m = TS_RE.search(body)
    return m.group(1) if m else ""


def merge(mine, theirs):
    pre_a, a = split_blocks(mine)
    pre_b, b = split_blocks(theirs)
    bd = {}
    for n, body in b:
        bd.setdefault(n, body)
    seen, out = set(), []
    for n, body in a:
        seen.add(n)
        other = bd.get(n)
        # ⛔ 只比區塊自己寫的時間。字串是 ISO 且時區固定 +08:00，直接比字典序是對的。
        if other is not None and ts(other) > ts(body):
            body = other
        out.append(body)
    for n, body in b:                    # 對方獨有的區塊：一定要留
        if n not in seen:
            out.append(body)
    return (pre_a or pre_b) + "".join(out)


def main(argv):
    if len(argv) != 3:
        print(__doc__.strip().splitlines()[2], file=sys.stderr)
        return 2
    with io.open(argv[1], encoding="utf-8") as f:
        mine = f.read()
    with io.open(argv[2], encoding="utf-8") as f:
        theirs = f.read()
    sys.stdout.write(merge(mine, theirs))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

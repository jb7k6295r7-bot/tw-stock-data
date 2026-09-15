#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tdcc.py — 集保戶股權分散表（大戶持股的來源）。

## 這支補的是哪個缺口

`db_status.py` 的「沒有來源」列著「集保流通股數」與「籌碼集中度的歷史序列」。
**大戶持股就是這份資料**——17 級分級裡高級距的人數與股數。

端點來自 WebSearch 結果、**不是自行生成**（`tw-data-sources` 3-4 的規矩）：

    https://opendata.tdcc.com.tw/getOD.ashx?id=1-5

2026-09-08 Actions 實測（`tdcc_probe.py`）：2.36 MB、68,867 列、4,051 檔，
每檔剛好 17 級，恆等式抽驗 200 檔 0 不符，對 `industry.csv` 涵蓋 99.9%
且分段全 100%（無截斷斷崖）。

## ⛔ 沒有歷史，只能每週累積

這支端點**不吃日期參數，只回最新一週**。資料日期是「每週最後一個營業日」，
週六 09:00 後產生。所以：

- **漏跑一週就永久少一週**，跟上櫃停牌同一種性質。排程要穩。
- 檔名用**資料自己宣告的日期**，不是今天——沙箱時鐘實測差過一天。

## 三道恆等式（來自 `tw-data-sources` 第四節第 10 項）

    ① 股數：合計 ＝ Σ(第 1～15 級) − 差異數調整
       人數：合計 ＝ Σ(第 1～15 級)   ← **不減調整**（2026-09-08 實測訂正）
    ② 每一檔都必須剛好 17 級
    ③ 整份只能有一個資料日期（多個代表這是累計檔）

⛔ **對不上就是抓錯期別或欄位錯位，整批丟棄，不要只修那一列。**

## ⚠ 分級代碼的意義本檔不宣稱

來源只給代碼（1～17），**沒有給級距文字**。第 1～15 級是持股級距、
另有「合計」與「差異數調整」兩列——這是 `tw-data-sources` 記載的結構，
本檔照它驗，但**每一級各自對應多少股，來源端沒說，本檔也不猜**。
要用「400 張以上」這種定義，得先從官方頁面查證級距對照表再寫進文件。
"""
import argparse
import csv
import io
import os
import sys

import backfill as B
from backfill import why as _W
import lowwater
import runlog

_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
OUT_DIR = os.path.join(_ROOT, "tdcc")
# ⭐⭐ 週檔是**累積**的：官方只給最近一期 ⇒ 漏一週就**永久少一週**。
#   ⛔ 而原本「已累積 N 週」只是 `rl.info` ⇒ 51 週變成 1 週也是 ✓。
#   ⚠ 而它會這樣少：整批覆蓋（四點六）、分支上的 `data/` 比 main 舊、
#     或某一趟在錯的 ref 上跑 ⇒ 三種都**不會報錯**，只是檔變少。
#   ⇒ 方向是 `UP`（越多越好）——⛔ 跟 `_missing_rows_low` 那幾個**相反**，
#     而它們的檔名長得一模一樣。別照抄語意（`lowwater.py` 檔頭）。
LOW = os.path.join(_ROOT, "meta", "_tdcc_weeks_low.txt")
IND = os.path.join(_ROOT, "meta", "industry.csv")

URL = "https://opendata.tdcc.com.tw/getOD.ashx?id=1-5"
HEADER = ["date", "stock_id", "level", "people", "shares", "pct"]

CODE_KEYS = ("證券代號", "股票代號", "代號")
DATE_KEYS = ("資料日期", "日期")
LEVEL_KEYS = ("持股分級", "分級")
PEOPLE_KEYS = ("人數",)
SHARE_KEYS = ("股數", "持股股數")
PCT_KEYS = ("占集保庫存數比例%", "占集保庫存數比例", "比例")

TOTAL_LEVEL = "17"        # 合計
ADJUST_LEVEL = "16"       # 差異數調整
N_LEVELS = 17


def pick(row, keys):
    for k in keys:
        v = row.get(k)
        if v is not None and str(v).strip() != "":
            return str(v).strip()
    return ""


def num(v):
    # ⛔ 不可以寫 `str(v or "")`：**整數 0 是 falsy**，會被換成空字串然後回 None，
    #   於是「這一格是 0」與「這一格沒有值」變得分不出來。CSV 來源全是字串
    #   （"0" 是 truthy）所以看不出問題，JSON 來源就會中——這種錯不會報錯，
    #   只會讓恆等式莫名其妙對不上。（2026-09-08 寫集保驗算時抓到）
    s = "" if v is None else str(v).replace(",", "").strip()
    try:
        return int(float(s))
    except ValueError:
        return None


def iso(v):
    """`20260904` → `2026-09-04`。抓不到就回空字串（**不猜**）。"""
    s = "".join(ch for ch in str(v) if ch.isdigit())
    return f"{s[:4]}-{s[4:6]}-{s[6:8]}" if len(s) == 8 else ""


def parse(raw):
    """→ (rows, note)。四種編碼都試，解不開就說出來。"""
    txt = None
    for enc in ("utf-8-sig", "utf-8", "big5", "cp950"):
        try:
            txt = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    if txt is None:
        return [], "四種編碼都解不開"
    # ⛔⛔ 2026-09-15 實測：2020 年有 6 份**開頭是兩個 BOM**
    #   （`efbbbf efbbbf 資料日期…`）⇒ `utf-8-sig` 只吃掉一個
    #   ⇒ 第一個欄名變成 `\ufeff資料日期` ⇒ 對不上 `DATE_KEYS`
    #   ⇒ ⛔ 那六週會被判成「缺 date 欄」而整批擋下。
    #   ⚠ 而這是**我方 parse() 的缺口**，不是那批資料壞——
    #     官方端點哪天多送一個 BOM，`main()` 會用一模一樣的方式壞掉。
    #   ⇒ ⭐ 剝掉**開頭所有**的 BOM（⛔ 不是剝一個）。
    txt = txt.lstrip("\ufeff")
    rows = list(csv.DictReader(io.StringIO(txt)))
    return rows, f"{len(rows):,} 列"


def cols_of(rows):
    """→ 這一份的欄名對照 `{"code":…, "level":…, "shares":…, "people":…,
    "date":…, "pct":…}`；缺哪一個就在 `missing` 裡。

    ⭐ 抽成函式的理由是四點五：`main()` 與 `import_hist()` **都要用**，
    ⛔ 而抄兩份就是那一族的第十次。
    """
    keys = (("code", CODE_KEYS), ("level", LEVEL_KEYS), ("shares", SHARE_KEYS),
            ("people", PEOPLE_KEYS), ("date", DATE_KEYS), ("pct", PCT_KEYS))
    got = {n: next((k for k in rows[0] if k in ks), None) for n, ks in keys}
    # ⚠ `pct` 不在必要清單裡（舊檔可能沒有）——⛔ 其餘五個少一個就不可以寫
    got["missing"] = [n for n in ("code", "level", "shares", "people", "date")
                      if not got[n]]
    return got


def week_facts(rows, c=None):
    """一份週檔的**三道驗算**。→ `(day, by, bad_lv, bad_ident, dates)`。

    ⭐⭐ 這是**唯一一份**實作（CLAUDE.md 四點五）。
    2026-09-15 之前它整段寫在 `main()` 裡 ⇒ 要匯入歷史檔就只能抄一份，
    ⛔ 而「同一個判準的兩份實作，只要外觀不同就躲得過 `selftest_no_dup`」。

        ③ `dates`      整份只能有一個資料日期（多個 ⇒ 這是累計檔，不是週檔）
        ② `bad_lv`     每一檔都必須剛好 17 級
        ① `bad_ident`  人數：合計 ＝ Σ(1~15)      ⛔ **不減**差異數調整
                       股數：合計 ＝ Σ(1~15) − 差異數調整
    ⚠ 兩條式子**不一樣**——照抄會讓人數那道在 66 檔上誤報（2026-09-08 實測）。
    """
    c = c or cols_of(rows)
    dates = {pick(r, DATE_KEYS) for r in rows} - {""}
    day = iso(sorted(dates)[0]) if dates else ""
    by = {}
    for r in rows:
        by.setdefault(str(r[c["code"]]).strip(), []).append(r)
    bad_lv = {k: len(v) for k, v in by.items() if len(v) != N_LEVELS}
    bad = {"人數": [], "股數": []}
    for code, rs in by.items():
        for label, key in (("人數", c["people"]), ("股數", c["shares"])):
            tot = adj = None
            parts = []
            for r in rs:
                lv = str(r[c["level"]]).strip()
                v = num(r[key])
                if v is None:
                    continue
                if lv == TOTAL_LEVEL:
                    tot = v
                elif lv == ADJUST_LEVEL:
                    adj = v
                else:
                    parts.append(v)
            if tot is None or not parts:
                continue
            want = sum(parts) - (adj or 0) if label == "股數" else sum(parts)
            if tot != want:
                bad[label].append(code)
    return day, by, bad_lv, bad, dates


def weeks_gate(rl):
    """「已累積幾週」的閘門。→ 週數。

    ⛔⛔ 2026-09-14 我第一版把它寫在 `main()` **最後面**
      ⇒ 而 `main()` 在「這一週的檔已經存在」時**早就 return 了**
      ⇒ ⭐ 那是**每天都會走的那條路** ⇒ 這道閘門一週只跑一次。
    ⚠ 而它要擋的事（目錄裡的週檔變少）**每天都可能發生**
      ——整份覆蓋、分支的 `data/` 比 main 舊、某趟在錯的 ref 上跑。
    ⇒ ⭐ 抽成函式，**每一條 return 之前都叫一次**。

    ⚠ 這正是 CLAUDE.md 第七點③那一族：**測了判準、沒測呼叫點**
      ——判準本身沒問題，⛔ 而它掛在一條「正常情況下走不到」的路上。
    """
    have = sorted(n[:-4] for n in os.listdir(OUT_DIR)
                  if n.endswith(".csv")) if os.path.isdir(OUT_DIR) else []
    rl.info("已累積", f"{len(have)} 週（{have[0]} ~ {have[-1]}）"
            if have else "⛔ **0 週**（⚠ 目錄是空的）")
    # ⛔ 原本這裡只有上面那一行 `rl.info` ⇒ **沒有任何一道在管週數會不會變少**。
    lowwater.gate(rl, LOW, len(have), lowwater.UP,
                  "集保週檔的累積週數（⛔ 官方只給最近一期，漏一週永久少一週）")
    return len(have)


HIST_DIR = os.path.join(_ROOT, "tdcc_hist")
HIST_COLS = ["date", "stock_id", "level", "people", "shares", "pct"]


def read_hist_week(path):
    """把一份**外部**週檔（.csv／.zip／.7z，內含單一 CSV）讀成 rows。

    ⚠ 使用者手上的封存是巢狀的：`<年>/<YYYYMMDD>.zip`（2019~2020）
    或 `.7z`（2021 起），裡面**只有一個** CSV。
    ⛔ 這裡不猜檔名——取壓縮檔裡的第一個檔。
    """
    if path.endswith(".csv"):
        return parse(io.open(path, "rb").read())
    if path.endswith(".zip"):
        import zipfile
        with zipfile.ZipFile(path) as z:
            return parse(z.read(z.namelist()[0]))
    if path.endswith(".7z"):
        import shutil as _sh
        import tempfile as _tf
        import py7zr
        d = _tf.mkdtemp()
        try:
            with py7zr.SevenZipFile(path) as z:
                z.extractall(d)
            f = [os.path.join(r, n) for r, _, ns in os.walk(d) for n in ns]
            return parse(io.open(f[0], "rb").read())
        finally:
            _sh.rmtree(d, ignore_errors=True)
    return [], f"不認得的副檔名：{path}"


def truncation_note(path):
    """→ 這一份是不是**被截斷**的（原因字串），不是就回空字串。⭐ 讀原始位元組。"""
    try:
        if path.endswith('.csv'):
            raw = io.open(path, 'rb').read()
        elif path.endswith('.zip'):
            import zipfile
            with zipfile.ZipFile(path) as z:
                raw = z.read(z.namelist()[0])
        elif path.endswith('.7z'):
            import shutil as _sh, tempfile as _tf, py7zr
            d = _tf.mkdtemp()
            try:
                with py7zr.SevenZipFile(path) as z:
                    z.extractall(d)
                f = [os.path.join(r, n) for r, _, ns in os.walk(d) for n in ns]
                raw = io.open(f[0], 'rb').read()
            finally:
                _sh.rmtree(d, ignore_errors=True)
        else:
            return ''
    except OSError:
        return ''
    return looks_truncated(raw)


def looks_truncated(raw):
    """→ 這一份是不是**被截斷**的（原因字串），不是就回 `""`。

    ⛔⛔ 2026-09-15 實測 `2023/20231020.7z`：解出來剛好 **1,572,864 bytes
      ＝ 1.5 MiB**（區塊邊界）、結尾**沒有換行**、最後一列只有 5 欄
      ⇒ 那一週少了一千多檔。
    ⚠ 而三道驗算是**碰巧**抓到它的（截斷落在列中間 ⇒ 那一檔只有 2 級）；
      ⛔ 落在**列邊界**上就三道全過，而幾百檔靜靜消失。
    ⇒ ⭐ 所以「是不是截斷」要**直接問**，⛔ 不要從別的症狀推。
    """
    if not raw:
        return ""
    why = []
    if not raw.endswith(b"\n") and not raw.endswith(b"\r"):
        why.append("檔尾沒有換行")
    txt = raw.decode("utf-8", "replace").lstrip("\ufeff")
    lines = txt.splitlines()
    if len(lines) >= 2:
        n_hdr = lines[0].count(",")
        if lines[-1].count(",") < n_hdr:
            why.append(f"最後一列只有 {lines[-1].count(',') + 1} 欄"
                       f"（表頭 {n_hdr + 1} 欄）")
    if len(raw) % 1024 == 0:
        why.append(f"大小剛好是 {len(raw) // 1024} KiB 的整數倍（⇒ 切在區塊邊界）")
    return "｜".join(why)


def hist_rows(rows, day, c=None):
    """→ 照 `HIST_COLS` 排好的 tuple list。⛔ 日期用**驗算算出來的** `day`，
    ⚠ 不是檔名——檔名與內容不一致時要以內容為準（第二點）。"""
    c = c or cols_of(rows)
    return [(day, str(r[c["code"]]).strip(), str(r[c["level"]]).strip(),
             pick(r, PEOPLE_KEYS), pick(r, SHARE_KEYS),
             pick(r, PCT_KEYS) if c["pct"] else "")
            for r in rows]


LEVELS_CSV = os.path.join(_ROOT, "meta", "tdcc_levels.csv")
LEVELS_HEADER = ["level", "lower", "upper_lo", "upper_hi", "exact", "n"]


def derive_levels(hist_dir=None):
    """從 `tdcc_hist/` **夾出** 15 個持股級距的邊界。→ (rows, note)。

    ## ⭐⭐ 這是**算出來的**，⛔ 不是抄坊間流傳的對照表

    `tdcc_probe.py` 自己寫著：「⛔ 我知道坊間流傳的對照表，但那是**間接證據**
    ——級距寫錯會讓『千張大戶』整個算錯。」
    ⇒ 而 370 週、2,061 萬列落地之後，它變成**夾得出來**的：

        每一級的「平均持股」＝ 股數 ÷ 人數，**必定落在該級的區間內**
        ⇒ b_k     ≥ 實測 max(avg_k)        （平均不可能超出上界）
          a_{k+1} ≤ 實測 min(avg_{k+1})    （平均不可能低於下界）
        而級距相鄰、股數是整數 ⇒ a_{k+1} = b_k + 1
        ⇒ ⭐ **max(avg_k) ≤ b_k ≤ min(avg_{k+1}) − 1**

    ⇒ 實測（2026-09-15，370 週）：**7 個邊界被夾成唯一解**
      （級 1 的 999、級 4 的 15,000、級 6/7/8 的 30,000/40,000/50,000、
        級 11/12 的 400,000/600,000），其餘每一格寬度都 ≤ 2 股，
      ⭐ 而 **14 格全部包含**坊間表那個數字。
      ⚠ 最寬的是級 10（89 股）——⛔ 那不是「算錯」，是那一級剛好沒有人
        在下界附近單獨持有。

    ## ⚠ 這個推導的**前提**（⛔ 不成立的話整套作廢）

    ① `人數` 是**持有人數**、`股數` 是他們的**總持股**
    ② 15 個級距**互斥且相鄰**（沒有縫、沒有重疊）
    ⇒ 兩條都是這張表的標準讀法，⛔ 而本檔**不宣稱**它們被證明過。

    ## ⭐ 而它直接回答了 E3 卡住的那件事

    第 15 級 = 1,000,001 股以上 ＝ **1,000 張以上** ⇒ 「千張大戶」就是第 15 級；
    400 張以上 ＝ 第 12 級起。
    """
    try:
        import numpy as np
        import pyarrow.parquet as pq
    except ImportError as ex:                                    # noqa: BLE001
        return [], f"⚠ 這台沒有 {ex.name}（⛔ 不是「算不出來」，是環境缺套件）"
    import glob as _g
    files = sorted(_g.glob(os.path.join(hist_dir or HIST_DIR, "*.parquet")))
    if not files:
        return [], "⛔ 沒有 tdcc_hist/*.parquet"
    lo, hi, n = {}, {}, {}
    for f in files:
        t = pq.read_table(f, columns=["level", "people", "shares"])
        lv = t.column("level").to_numpy()
        pe = t.column("people").to_numpy(zero_copy_only=False)
        sh = t.column("shares").to_numpy(zero_copy_only=False)
        ok = (pe > 0) & (sh > 0) & (lv >= 1) & (lv <= N_LEVELS - 2)
        avg, L = sh[ok] / pe[ok], lv[ok]
        for k in range(1, N_LEVELS - 1):
            m = L == k
            if not m.any():
                continue
            a = avg[m]
            lo[k] = min(lo.get(k, float("inf")), float(a.min()))
            hi[k] = max(hi.get(k, 0.0), float(a.max()))
            n[k] = n.get(k, 0) + int(m.sum())
    rows = []
    for k in sorted(lo):
        lower = 1 if k == 1 else int(round(hi[k - 1])) + 1
        if k + 1 in lo:
            ub_lo, ub_hi = int(round(hi[k])), int(lo[k + 1]) - 1
        else:
            ub_lo, ub_hi = 0, 0                 # 最高一級沒有上界
        rows.append([k, lower, ub_lo, ub_hi,
                     "1" if (ub_hi and ub_lo == ub_hi) else "0", n.get(k, 0)])
    n_exact = sum(1 for r in rows if r[4] == "1")
    return rows, (f"{len(rows)} 級｜{n_exact} 個邊界夾成唯一解"
                  f"｜樣本 {sum(n.values()):,} 列")


def levels_gaps(rows):
    """→ 接不起來的地方 `[(級, 上界, 下一級下界), ...]`。

    ⛔ 級距必須**相鄰**：`a_{k+1} = b_k + 1`。⚠ 接不起來就代表
    ① 我方的推導前提錯了，或 ② 官方改過級距 ⇒ 兩種都要人看，**不可以自動放行**。
    """
    bad = []
    for i, r in enumerate(rows[:-1]):
        nxt = rows[i + 1]
        if r[3] and nxt[1] != r[3] + 1 and nxt[1] != r[2] + 1:
            bad.append((r[0], r[3], nxt[1]))
    return bad


def import_hist(rl, src, out_dir=None, apply=False):
    """把一整個目錄的外部週檔收成 `tdcc_hist/<年>.parquet`。→ rc。

    ## ⛔ 每一週都要過那三道驗算，**不過就不寫**

    ⚠ 這批是**外部來源**（使用者自 2019 起每週手動下載的封存）
    ⇒ 它比官方端點更需要驗：端點至少會回一致的格式，
    ⛔ 而一份放了七年的封存，任何一週壞掉都不會有人知道。
    ⇒ 判準跟 `main()` **同一份**（`week_facts`），⛔ 不另寫一套。

    ## ⭐⭐ 而重疊的那幾週是【閘門】，不是「跳過」

    `data/tdcc/` 已經有我方自己抓的幾週。⚠ 那幾週兩邊都有
    ⇒ ⭐ **拿來逐格對**：對不上就整批不寫。
    ⛔ 這是這批外部資料唯一一個**獨立**的驗證點——
    放掉它，就只剩「它自己跟自己一致」（C 級）。

    ## ⚠ 而日期以**內容**為準，⛔ 不是檔名

    檔名 `20190628.zip` 只是人取的；`資料日期` 欄才是它自己講的（第二點）。
    ⇒ 兩者不一致就當作壞檔擋下來。
    """
    import glob as _g
    out_dir = out_dir or HIST_DIR
    files = sorted(_g.glob(os.path.join(src, "*", "*.zip"))
                   + _g.glob(os.path.join(src, "*", "*.7z"))
                   + _g.glob(os.path.join(src, "*", "*.csv")))
    rl.info("來源", f"{src}｜{len(files)} 份週檔")
    if not files:
        rl.check("找得到週檔", False, f"{src} 底下一份都沒有")
        return rl.finish()

    by_year, bad_files, name_mismatch = {}, [], []
    seen_day, dup_same, dup_diff = {}, [], []
    n_codes = {}
    n_rows = 0
    for path in files:
        rows, note = read_hist_week(path)
        base = os.path.basename(path).split(".")[0]
        trunc = truncation_note(path)
        if trunc:
            bad_files.append((base, f"⛔ **被截斷**：{trunc}"))
            continue
        if not rows:
            bad_files.append((base, f"讀不到列（{note}）"))
            continue
        c = cols_of(rows)
        if c["missing"]:
            bad_files.append((base, f"缺欄 {c['missing']}"))
            continue
        day, by, bad_lv, bad, dates = week_facts(rows, c)
        if len(dates) != 1 or not day:
            bad_files.append((base, f"資料日期 {len(dates)} 個：{sorted(dates)[:3]}"))
            continue
        if bad_lv:
            bad_files.append((base, f"{len(bad_lv)} 檔不是 {N_LEVELS} 級"))
            continue
        if bad["人數"] or bad["股數"]:
            bad_files.append((base, f"恆等式不符 人數 {len(bad['人數'])}"
                                    f"／股數 {len(bad['股數'])}"))
            continue
        # ⚠ 檔名與內容講的日期不一致 ⇒ 記下來（⛔ 但以內容為準）
        if base.isdigit() and iso(base) != day:
            name_mismatch.append((base, day))
        recs = hist_rows(rows, day, c)
        if day in seen_day:
            # ⛔⛔ 同一個資料日期出現兩次。⚠ 兩種成因，處置相反
            #   （形狀照 `adjust.halting_event_is_real()`：**算出來的**歸因，
            #     ⛔ 不是一份寫死的黑名單——下一次重複的會是別的日期）：
            #
            #   ① 兩份內容**逐格相同** ⇒ 封存裡有人把同一週存了兩個檔名
            #      ⇒ 丟掉後來那一份，⭐ 而且要**講出那個檔名的週其實沒有**
            #   ② 內容**不同**        ⇒ ⛔ 這是真的矛盾，整批不可以寫
            #
            # 【實測 2026-09-15】`20200619.zip` 與 `20200612.zip` 逐位元相同
            #   ⇒ 2020-06-19 那一週**其實沒有**，⚠ 而檔名看起來像有。
            prev_name, prev = seen_day[day]
            if recs == prev:
                dup_same.append((base, prev_name, day))
            else:
                dup_diff.append((base, prev_name, day))
            continue
        seen_day[day] = (base, recs)
        n_codes[day] = (len(by), os.path.getsize(path))
        by_year.setdefault(day[:4], []).extend(recs)
        n_rows += len(rows)

    rl.info("驗算通過", f"{len(files) - len(bad_files)} / {len(files)} 週"
                        f"｜{n_rows:,} 列")
    for b, why in bad_files[:10]:
        rl.info(f"  ⛔ {b}", why)
    # ⛔⛔ 這裡**逐週排除**，不是整批不寫。
    #   ⚠ `tdcc.py` 檔頭那句「對不上就整批丟棄」是對**那一週**說的
    #   ——⛔ 不是「一週壞掉就賠掉另外 371 週」。
    #   ⇒ 壞掉的那幾週**不寫**（⛔ 絕不寫部分資料），⭐ 而且逐筆講出原因。
    if bad_files:
        rl.info("⛔ 排除的週（**不寫**，⚠ 那幾週就是缺）",
                f"{len(bad_files)} 份："
                + "｜".join(f"{b}（{why}）" for b, why in bad_files[:8]))
    # ⭐ 而「系統性壞掉」要自己有一道：少數壞掉是封存的事，
    #   ⛔ 大部分壞掉就是我方讀法錯了（例如換了格式而我沒跟上）。
    rate = (len(files) - len(bad_files)) / len(files) if files else 0
    # ⛔⛔ 母體太小的時候這道**判不出來**：2 份裡 1 份壞是 50%，
    #   ⚠ 而那既可能是封存壞了一份，也可能是我方讀錯——**分不出**。
    #   ⇒ ⭐ 分不出就大聲說分不出，⛔ 不可以假裝判過（也不可以假紅）。
    RATE_MIN_N = 20
    if len(files) < RATE_MIN_N:
        rl.info("⚠⚠ **這一層沒跑**：通過率",
                f"只有 {len(files)} 份（< {RATE_MIN_N}）⇒ 分不出「封存壞一份」"
                f"還是「我方讀錯」　⇒ ⛔ 不算失敗，⛔ **也不算驗過**"
                f"｜本趟 {len(files) - len(bad_files)}/{len(files)}")
        rate_ok = True
    else:
        rate_ok = rate >= 0.95
        rl.check("⭐⭐ 通過率 ≥ 95%（⛔ 少數壞掉是封存的事，**大部分**壞掉是我方讀錯）",
                 rate_ok,
                 f"{len(files) - len(bad_files)} / {len(files)}（{rate * 100:.1f}%）")
    # ⛔ 檔名與內容不一致**不算失敗**：內容才是判準（第二點），而檔名是人取的。
    #   ⚠ 但一定要講出來——⭐ 否則「372 個檔」會被讀成「372 週」。
    if name_mismatch:
        rl.info("⚠ 檔名與內容講的日期不一致（⭐ 以**內容**為準）",
                f"{len(name_mismatch)} 份：{name_mismatch[:5]}"
                "　⇒ ⛔ 不算失敗，⚠ 而那幾個檔名的週**不必然存在**")
    if dup_same:
        rl.info("⚠⚠ 同一週被存成兩個檔名（內容逐格相同 ⇒ 丟掉後來那份）",
                f"{len(dup_same)} 組：{dup_same[:5]}"
                "　⇒ ⛔ **那幾個檔名對應的週其實沒有**，"
                "⚠ 別把檔案數當成週數")
    rl.check("⛔ 同一個資料日期的兩份內容**不可以不同**（⚠ 那是真的矛盾）",
             not dup_diff,
             f"⛔ {len(dup_diff)} 組矛盾：{dup_diff[:5]}" if dup_diff
             else f"{len(seen_day)} 週沒有矛盾")

    # ⭐⭐ 檔數的**斷崖**：一份被截斷的週檔，證券會從某一個代號之後整批消失
    #
    # ⛔⛔ 2026-09-15 實測：`2023/20231020.7z` 解出來剛好 **1,572,864 bytes
    #   ＝ 1.5 MiB**，結尾沒有換行、最後一列切在一半 ⇒ 那一週只有 2,787 檔，
    #   而同年其他週是 4,000 出頭 ⇒ **一千多檔整批不見**。
    # ⚠⚠ 而三道驗算**差一點就全過**：這次只因為截斷剛好落在**列中間**
    #   （8162 只有 2 級）才被「非 17 級」那道碰巧抓到。
    #   ⛔ 截斷若落在**列邊界**上，每一檔都剛好 17 級、恆等式也都成立
    #   ⇒ 三道全過，而幾百檔靜靜消失。
    # ⇒ ⭐ 所以檔數要**自己有一道**，⛔ 不可以靠那三道順便。
    #
    # ⚠ 門檻用**同年的中位數**，⛔ 不是寫死一個數字：檔數逐年在長
    #   （2019 約 2,689 → 2026 約 4,055）⇒ 寫死的門檻對某幾年一定是錯的。
    cliffs = []
    by_year_codes = {}
    for day, (n, _sz) in n_codes.items():
        by_year_codes.setdefault(day[:4], []).append((day, n))
    for year, pairs in sorted(by_year_codes.items()):
        med = sorted(n for _d, n in pairs)[len(pairs) // 2]
        for day, n in sorted(pairs):
            if med and n < med * 0.9:
                cliffs.append((day, n, med, n_codes[day][1]))
    rl.info("⭐ 逐年檔數（中位數）",
            "｜".join(f"{y} {sorted(n for _d, n in v)[len(v)//2]:,}"
                      for y, v in sorted(by_year_codes.items())))
    rl.check("⭐⭐ 沒有哪一週的檔數對同年中位數**斷崖**（< 90%）"
             "　⚠ 截斷的週檔就長這樣，⛔ 而三道驗算抓不到它",
             not cliffs,
             f"⛔ {len(cliffs)} 週斷崖："
             + "｜".join(f"{d} {n:,}檔 vs 中位 {m:,}（檔 {sz:,} bytes）"
                         for d, n, m, sz in cliffs[:5])
             if cliffs else f"{len(n_codes)} 週都在中位數 90% 以上")

    # ⭐⭐ 重疊那幾週是**閘門**：跟 `data/tdcc/` 我方自己抓的逐格對
    ours, same, diff = {}, 0, []
    if os.path.isdir(OUT_DIR):
        for f in sorted(os.listdir(OUT_DIR)):
            if f.endswith(".csv"):
                ours[f[:-4]] = os.path.join(OUT_DIR, f)
    for day, path in sorted(ours.items()):
        mine = by_year.get(day[:4], [])
        theirs = {(r[1], r[2]): (r[3], r[4]) for r in mine if r[0] == day}
        if not theirs:
            continue
        with io.open(path, encoding="utf-8") as f:
            got = {(r["stock_id"], r["level"]): (r["people"], r["shares"])
                   for r in csv.DictReader(f)}
        bad_cells = [k for k in set(got) & set(theirs) if got[k] != theirs[k]]
        only = len(set(got) ^ set(theirs))
        if bad_cells or only:
            diff.append((day, len(bad_cells), only))
        else:
            same += 1
    if not ours or not any(d[:4] in by_year for d in ours):
        # ⭐ 寫成不會被讀成「驗過了」的樣子
        rl.info("⚠⚠ **這一層沒跑**",
                "外部封存與 `data/tdcc/` **沒有重疊的週**"
                "　⇒ ⛔ 不算失敗，⛔ **也不算驗過**"
                "　⚠ 那表示這批資料只有「自己跟自己一致」")
    else:
        rl.check("⭐⭐ 重疊的週跟我方自己抓的**逐格相同**"
                 "（⛔ 這是唯一一個獨立驗證點）",
                 not diff,
                 f"⛔ {len(diff)} 週對不上：{diff[:3]}" if diff
                 else f"{same} 週逐格相同")
    if not rate_ok or dup_diff or diff or cliffs:
        rl.info("⛔ 有沒過的驗算 ⇒ **一個檔都不寫**", "先把上面那幾項弄清楚")
        return rl.finish()

    rl.info("分年", "｜".join(f"{y} {len({r[0] for r in v})} 週／{len(v):,} 列"
                             for y, v in sorted(by_year.items())))
    if not apply:
        rl.info("⚠ 這一趟沒有 `--apply`", "只驗不寫")
        return rl.finish()
    written = write_hist(by_year, out_dir)
    rl.info("寫出", "｜".join(f"{y} {sz/1048576:.1f} MB" for y, sz in written))
    rl.check("⭐ 寫完重讀，列數與週數逐年對得回來（⛔ 不是斷言寫檔成功）",
             *verify_hist(by_year, out_dir))
    return rl.finish()


def levels_cmd(rl, apply=False, hist_dir=None, out=None):
    """夾出級距對照表並寫成 `data/meta/tdcc_levels.csv`。→ rc。"""
    rows, note = derive_levels(hist_dir)
    rl.info("⭐ 這一支在做什麼",
            "從我方自己的 370 週資料**夾出**持股級距的邊界"
            "　⛔ 不是抄坊間流傳的對照表（那是間接證據，"
            "⚠ 而級距寫錯會讓「千張大戶」整個算錯）")
    rl.info("推導", "b_k ≥ max(股數÷人數 的實測)｜a_{k+1} ≤ min(…)｜"
                    "而 a_{k+1} = b_k + 1（級距相鄰、股數是整數）"
                    "　⇒ **max(avg_k) ≤ b_k ≤ min(avg_{k+1}) − 1**")
    if not rows:
        # ⭐ 寫成不會被讀成「驗過了」的樣子
        rl.info("⚠⚠ **這一層沒跑**", f"{note}　⇒ ⛔ 不算失敗，⛔ **也不算驗過**")
        return rl.finish()
    rl.info("結果", note)
    for r in rows:
        ub = f"{r[2]:,} ~ {r[3]:,}" if r[3] else "（無上限）"
        rl.info(f"  第 {r[0]:>2} 級",
                f"{r[1]:>9,} 股起｜上界夾在 {ub}"
                + ("　⭐ **唯一解**" if r[4] == "1" else "")
                + f"｜樣本 {r[5]:,}")
    rl.check("⭐ 15 級都夾得出來（⛔ 少一級就不可以寫）",
             len(rows) == N_LEVELS - 2, f"{len(rows)} 級")
    gaps = levels_gaps(rows)
    rl.check("⭐⭐ 級距**接得起來**（a_{k+1} = b_k + 1，⛔ 沒有縫也沒有重疊）",
             not gaps, f"⛔ {gaps}" if gaps else f"{len(rows)} 級連續")
    n_exact = sum(1 for r in rows if r[4] == "1")
    rl.check("⭐ 至少 5 個邊界被夾成**唯一解**"
             "（⛔ 一個都沒有就代表樣本不夠，這張表不可以當判準）",
             n_exact >= 5, f"{n_exact} 個唯一解")
    # ⭐⭐ 而「千張大戶」那一格要自己講出來——⛔ 那是 E3 卡住的原因
    top = rows[-1]
    rl.info("⭐⭐ 「千張大戶」落在哪一級",
            f"第 {top[0]} 級 ＝ {top[1]:,} 股以上 ＝ **{top[1] // 1000:,} 張以上**"
            f"　⇒ 400 張以上是第 "
            f"{next((r[0] for r in rows if r[1] >= 400_000), '?')} 級起")
    if not apply:
        rl.info("⚠ 這一趟沒有 `--apply`", "只算不寫")
        return rl.finish()
    path = out or LEVELS_CSV
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with io.open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(LEVELS_HEADER)
        w.writerows(rows)
    # ⭐ 寫完**重讀**（四點二：斷言要驗終點）
    with io.open(path, encoding="utf-8") as f:
        back = list(csv.reader(f))
    rl.check("⭐ 寫完重讀，表頭與列數對得回來（⛔ 不是斷言寫檔成功）",
             back and back[0] == LEVELS_HEADER and len(back) - 1 == len(rows),
             f"讀回 {len(back) - 1} 列｜表頭 {back[0] if back else '(空)'}")
    return rl.finish()


def write_hist(by_year, out_dir):
    """一年一個 parquet。→ [(年, 位元組)]。

    ⭐ 先照 `(stock_id, level, date)` 排序**才**寫：同一檔同一級的 52 週
    連在一起 ⇒ `people`／`shares` 的 delta 壓得掉。
    實測 2026 全年 80.0 MB → **8.7 MB（10.8%）**；不排序是 2.4 倍大。
    """
    import pyarrow as pa
    import pyarrow.parquet as pq
    os.makedirs(out_dir, exist_ok=True)
    out = []
    for year, recs in sorted(by_year.items()):
        recs.sort(key=lambda r: (r[1], num(r[2]) or 0, r[0]))
        tbl = pa.table({
            "date": pa.array([r[0] for r in recs]).dictionary_encode(),
            "stock_id": pa.array([r[1] for r in recs]).dictionary_encode(),
            "level": pa.array([num(r[2]) for r in recs], pa.int8()),
            "people": pa.array([num(r[3]) for r in recs], pa.int64()),
            "shares": pa.array([num(r[4]) for r in recs], pa.int64()),
            "pct": pa.array([_f(r[5]) for r in recs], pa.float32()),
        })
        p = os.path.join(out_dir, f"{year}.parquet")
        pq.write_table(tbl, p, compression="zstd", compression_level=9)
        out.append((year, os.path.getsize(p)))
    return out


def verify_hist(by_year, out_dir):
    """⭐ 寫完**重讀**（四點二：斷言要驗終點）。→ (通過, 說明)。"""
    import pyarrow.parquet as pq
    bad = []
    for year, recs in sorted(by_year.items()):
        p = os.path.join(out_dir, f"{year}.parquet")
        if not os.path.exists(p):
            bad.append((year, "檔不在"))
            continue
        t = pq.read_table(p)
        got_rows = t.num_rows
        got_weeks = len(set(t.column("date").to_pylist()))
        want_weeks = len({r[0] for r in recs})
        if got_rows != len(recs) or got_weeks != want_weeks:
            bad.append((year, f"讀回 {got_rows:,} 列／{got_weeks} 週"
                              f"，應該是 {len(recs):,}／{want_weeks}"))
    return (not bad,
            f"⛔ {bad}" if bad else
            f"{len(by_year)} 年逐年重讀，列數與週數都對得回來")


def _f(x):
    try:
        return float(x)
    except (ValueError, TypeError):
        return None


def main():
    ap = argparse.ArgumentParser(description="集保戶股權分散表（每週）")
    ap.add_argument("--run", action="store_true", help="抓最新一週並寫檔")
    ap.add_argument("--force", action="store_true", help="已存在也重寫")
    ap.add_argument("--import-hist", metavar="DIR",
                    help="把 <DIR>/<年>/<YYYYMMDD>.{zip,7z,csv} 收成 tdcc_hist/<年>.parquet")
    ap.add_argument("--levels", action="store_true",
                    help="從 tdcc_hist 夾出持股級距對照表 → data/meta/tdcc_levels.csv")
    ap.add_argument("--apply", action="store_true",
                    help="⭐ 真的寫檔；⛔ 不帶就只驗不寫")
    a = ap.parse_args()
    if a.levels:
        return levels_cmd(runlog.Run("tdcc_levels"), apply=a.apply)
    if a.import_hist:
        return import_hist(runlog.Run("tdcc_hist"), a.import_hist, apply=a.apply)
    if not a.run:
        ap.print_help()
        return 1

    rl = runlog.Run("tdcc")
    raw, err = B.get(URL, retries=3, timeout=120)
    if err:
        print(f"[tdcc] 請求失敗：{_W(err, 160)}", file=sys.stderr)
        rl.check("端點有回應", False, _W(err, 100))
        return rl.finish()
    rows, note = parse(raw)
    print(f"[tdcc] {len(raw):,} bytes｜{note}")
    if not rows:
        rl.check("解析得到列", False, note)
        return rl.finish()

    # ⭐ 欄名對照與三道驗算都走**唯一一份**（`cols_of`／`week_facts`，四點五）
    c = cols_of(rows)
    code_k, lvl_k, shr_k = c["code"], c["level"], c["shares"]
    ppl_k, date_k, pct_k = c["people"], c["date"], c["pct"]
    missing = c["missing"]
    if missing:
        # ⛔ 欄位對不上就整批不寫。**把實際表頭印出來**，不然下次還是只能猜。
        print(f"[tdcc] 欄位對不上，缺 {missing}；實際表頭 {list(rows[0])}",
              file=sys.stderr)
        rl.check("欄位對得上", False, f"缺 {missing}｜實際 {list(rows[0])}")
        return rl.finish()

    day, by, bad_lv, bad, dates = week_facts(rows, c)

    # ── ③ 整份只能有一個資料日期 ──
    rl.info("資料日期", f"{day}（原始 {sorted(dates)}）")
    ok_date = len(dates) == 1 and bool(day)
    rl.check("整份只有一個資料日期（單週檔）", ok_date,
             f"{len(dates)} 個：{sorted(dates)[:3]}")

    # ── ② 每一檔剛好 17 級 ──
    rl.info("證券檔數", f"{len(by):,}｜總列數 {len(rows):,}")
    rl.check(f"每一檔都剛好 {N_LEVELS} 級", not bad_lv,
             f"{len(bad_lv)} 檔不是：{list(bad_lv.items())[:5]}" if bad_lv
             else f"{len(by):,} 檔全對")

    # ── ① 恆等式。⚠⚠ **人數與股數的式子不一樣**（2026-09-08 實測訂正）──
    #
    #   股數：合計 ＝ Σ(1~15) − 差異數調整
    #   人數：合計 ＝ Σ(1~15)      ← **不減差異數調整**
    #
    #   第一版兩欄都用「減調整」，結果股數 4,051 檔全過、**人數 66 檔不符**，
    #   整批被自己的驗算擋下、那一週一列都沒寫。
    #   探針把不符的 17 列原樣印出來之後就看懂了——差值**恰好等於第 16 級的人數**：
    #       00406A  合計 135,240 ＝ Σ(1~15) 135,240，第 16 級人數 5
    #       0050    合計 3,537,377 ＝ Σ(1~15) 3,537,377，第 16 級人數 1
    #   「差異數調整」是**集保庫存與發行股數的差額**，它調整的是股數；
    #   那一列的人數是該筆調整涉及的戶數，**本來就不從合計裡扣**。
    #
    #   ⚠ 為什麼拖到正式抓取才爆：其餘 3,985 檔的第 16 級人數是 0，
    #     減不減都一樣。**只有那 66 檔的第 16 級人數 ≠ 0 才暴露得出來。**
    #     這就是為什麼探針抽驗 200 檔沒事——它抽到的剛好都是 0 的。
    #
    #   ⛔ 這是**改對公式**，不是放寬驗算：兩道都還在，只是人數那道用對的式子。
    for label, formula in (("人數", "合計 ＝ Σ(1~15)（不減差異數調整）"),
                           ("股數", "合計 ＝ Σ(1~15) − 差異數調整")):
        rl.check(f"恆等式（{label}）{formula}",
                 not bad[label],
                 f"{len(bad[label])} 檔不符：{bad[label][:5]}" if bad[label]
                 else f"{len(by):,} 檔全過")

    # ── 涵蓋率（分段看，截斷是斷崖不是均勻地少）──
    ok_seg = True          # 沒有 industry.csv 可對時視為通過（答不出來就不誤殺）
    if os.path.exists(IND):
        want = {r["stock_id"] for r in
                csv.DictReader(io.open(IND, encoding="utf-8"))}
        hit = want & set(by)
        rl.info("涵蓋", f"母體 {len(want):,} 檔命中 {len(hit):,} 檔"
                        f"（{len(hit) / len(want) * 100:.1f}%）")
        seg = []
        for lo in range(1000, 10000, 1000):
            s = {c for c in want if c.isdigit() and lo <= int(c) < lo + 1000}
            if s:
                seg.append(len(s & set(by)) / len(s) * 100)
        ok_seg = all(x > 50 for x in seg)
        rl.check("涵蓋率沒有斷崖（每個代號千位段都 > 50%）", ok_seg,
                 "最低段 " + (f"{min(seg):.0f}%" if seg else "—"))

    # ⛔ 任何一道恆等式沒過就整批不寫。對不上就是抓錯期別或欄位錯位，
    #    寫進去等於把錯的數字混進資料庫，而它看起來完全正常。
    # ⛔ 涵蓋率斷崖也算致命：**一份被截斷、卻看起來完整的週檔**混進資料庫之後
    #    分不出來——截斷是無聲的，每一列都是真的，只是少了後面。
    fatal = (bad["人數"] or bad["股數"] or bad_lv or not ok_date or not ok_seg)
    if fatal:
        print("[tdcc] ★ 驗算沒過，**整批不寫**。對不上就是抓錯期別或欄位錯位，"
              "不要只修那一列。", file=sys.stderr)
        # ★ 讓看 runlog 的人知道「這一週是不是就此永久缺了」——
        #   2026-09-08 的 tdcc_probe 第 5 節在查詢頁看到 51 個資料日期選項
        #   （20250912 ~ 20260904），所以**擋下來不等於永久失去**，補得回來。
        #   ⚠ 但那還只是「頁面上有下拉選單」這種間接證據；探針第 7 節才真的
        #     去打舊週別驗它。在第 7 節答出來之前，這句話只能這樣寫。
        rl.note("擋下來的這一週不必然永久缺：查詢頁列了 51 個歷史週別"
                "（待 tdcc_probe 第 7 節實測確認真的抓得到）")
        return rl.finish()

    path = os.path.join(OUT_DIR, f"{day}.csv")
    if os.path.exists(path) and not a.force:
        rl.note(f"{day} 已存在，跳過（--force 可覆寫）")
        print(f"[tdcc] {path} 已存在，跳過")
        # ⭐ ⛔ 這條是**每天都會走的**那條路（一週只有一天會寫新檔）
        #   ⇒ 閘門一定要在這裡也跑一次，否則它一週只守一天。
        weeks_gate(rl)
        return rl.finish()
    os.makedirs(OUT_DIR, exist_ok=True)
    out = []
    for r in rows:
        out.append([day, str(r[code_k]).strip(), str(r[lvl_k]).strip(),
                    pick(r, PEOPLE_KEYS), pick(r, SHARE_KEYS),
                    pick(r, PCT_KEYS) if pct_k else ""])
    out.sort(key=lambda x: (x[1], int(x[2]) if x[2].isdigit() else 99))
    with io.open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(HEADER)
        w.writerows(out)
    print(f"[tdcc] 寫出 {path}（{len(out):,} 列）")
    rl.info("寫出", f"{day}.csv（{len(out):,} 列）")
    weeks_gate(rl)
    return rl.finish()


if __name__ == "__main__":
    sys.exit(main())

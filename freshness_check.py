#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""freshness_check.py — 「不累積就永久失去」的那幾份，有沒有真的在累積。**只讀 repo。**

## 為什麼要有這一支

2026-09-09 查出來的東西裡，有一類跟其他缺口性質完全不同：

> **官方只保留一段時間，今天沒抓，一年後（或下個月）就永遠沒有。**

目前已知三份：

| 資料 | 官方保留多久 | 我方怎麼累積 |
|---|---|---|
| 集保股權分散表 `data/tdcc/` | **一年**（官方文件明寫） | 每週一份 |
| 股本／面額原始快照 `data/universe/capital/` | 只給當期 | 每趟一份（依出表日期） |
| 天然災害停止上班原始頁 `data/holiday/` | 只給當天 | 每天一份 |
| 開休市行事曆 `holiday_schedule.csv` | **只給當年** | 每天併入 |

⛔ 而它們全部掛在 `continue-on-error: true` 的步驟上——
**壞掉的時候整條管線是綠的**，而且要等到有人想用歷史才會發現，那時已經來不及。

## 這一支只做一件事

**看最新的一份有多舊。** 超過各自的容忍天數就 `rl.check` 失敗（整支 exit 1）。

⛔ 容忍天數要比「正常週期」寬一點，但**不可以寬到失去意義**：
集保每週一份 ⇒ 容忍 **10 天**（週期 7 天 ＋ 一次失敗的緩衝），
⛔ 不是 30 天——30 天代表可以連錯四週才被發現。

⚠ 這一支**不驗內容**，只驗新舊。內容的檢查在各自的腳本裡。
"""
import glob
import io
import os
import re
import sys
from datetime import datetime, timedelta, timezone

import runlog

TPE = timezone(timedelta(hours=8))
_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")

# (名稱, 目錄或檔案, 從哪裡取日期, 容忍天數, 為什麼是這個數)
TARGETS = [
    ("集保股權分散表", os.path.join(_ROOT, "tdcc"), "filename", 10,
     "每週一份；10 天 ＝ 週期 7 ＋ 一次失敗的緩衝。⛔ 官方只留一年，補不回來"),
    ("股本快照 twse", os.path.join(_ROOT, "universe", "capital",
                                 "twse-opendata-L"), "filename_roc", 40,
     "每月一趟；40 天 ＝ 週期 31 ＋ 緩衝"),
    ("股本快照 tpex", os.path.join(_ROOT, "universe", "capital",
                                 "tpex-mopsfin-O"), "filename_roc", 40,
     "同上"),
    ("天然災害停班原始頁", os.path.join(_ROOT, "holiday"), "filename", 5,
     "每個交易日一份；5 天 ＝ 連假 ＋ 一次失敗"),
    ("開休市行事曆", os.path.join(_ROOT, "meta", "holiday_schedule.csv"),
     "asof_column", 5, "每天併入；看 `asof` 欄最新值"),
    # ★ 2026-09-09 新增。櫃買那 8 個「歷史指數」端點**每一個都只回 7 列**
    #   （swagger 寫「歷史」是誤導）⇒ 這是上櫃交易日曆的唯一外部判準，
    #   而且**不累積就永久失去**，跟集保同一族。
    #   5 天 ＝ 連假 ＋ 一次失敗；⛔ 拖到第 8 天就會有一天永遠拿不到判準。
    ("上櫃交易日曆判準", os.path.join(_ROOT, "meta", "calendar_tpex.csv"),
     "asof_column", 5,
     "每天併入；端點只給最近 7 個交易日 ⇒ 斷超過 7 天就有日子永遠補不回來"),
    # ⭐⭐ 2026-09-11 新增。上市「**停止買賣中**」（`violation/stop`）。
    #   ⛔ 它**只給當下那一份、沒有任何歷史**（`date=` 官方忽略）
    #   ⇒ 漏抓一天就**永久少一天**，跟集保、上櫃日曆同一族。
    #
    # ⚠ 而它為什麼重要，是今天算出來的：
    #   `hole_kinds` 裡 `uncovered`（判不出來）那一類**100% 是上市**——
    #   因為 `chtm.halted` 是**櫃買**的表，上市沒有對應的逐日序列。
    #   ⇒ 上市最長的那幾個洞（6131 鈞泰 218 天、4414 如興 203 天、
    #     3018 隆銘綠能 144 天）我方**一段都解釋不了**。
    #   ⛔ 而現成的 `meta/suspend.csv` 補不上這個洞：10,034 列裡 9,594 列是
    #     權證（`sec_kind=其他`）、普通股只有 409 列 ⇒ 62 段只解釋得了 **3 段**。
    #
    # ⇒ ⭐ 這一支**追不回過去**，但它決定了「從今天起會不會繼續失去」。
    #   ⚠ 所以它必須在這一節，⛔ 不是只掛在 daily.yml 裡等人發現它沒跑。
    ("上市停止買賣中名單", os.path.join(_ROOT, "universe", "stophalt"),
     "filename", 5,
     "每個交易日一份；⛔ 官方只給當下、沒有歷史 ⇒ 漏一天永久少一天。"
     "5 天 ＝ 連假 ＋ 一次失敗"),
    # ⭐⭐ 2026-09-24 新增：幣市日 K。⛔ 在這之前【完全沒有任何一道】在守它的新鮮度。
    #   ⚠ 而 crypto.py 自己那條「本趟不是全失敗」在「成功 0／失敗 0」時也會過
    #   ⇒ 2026-09-23 那趟 15 幣全部 +0 列，runlog 照樣 ✓ 正常
    #   ⇒ 資料停在 09-21 兩天，⛔ 沒有任何地方會說。
    # ⭐ 用 BTC 當代表：同一趟抓 15 幣，BTC 停了就是整趟停了
    #   （⚠ 單一幣缺漏是另一件事，⛔ 這一條不管）
    # ⭐ 看 asof 欄：那是【我方寫進來】的日期 ⇒ 空跑那一趟 asof 不會前進
    #   ⇒ 正好量的是「多久沒拿到新資料」，⛔ 不是「資料本身是哪一天」
    # 3 天 ＝ 每天一趟 ＋ 一次失敗 ＋ 上傳延遲一天（幣市週末也交易，⛔ 沒有連假）
    # ⭐⭐ 2026-09-24 新增：大盤三大法人金額。⛔ 在這之前沒有任何一道在守它。
    #   ⚠ 它跟上面四份【性質不同】：T86 指定日期抓得到 ⇒ 這一份【補得回來】。
    #     ⇒ 放這裡的理由不是「失去就永久」，而是它會【安靜停住】：
    #       ・寫它那一步掛 continue-on-error ⇒ 壞掉那天整條管線是綠的
    #       ・crosscheck ① 只掃檔案裡【已有的日子】⇒ 停止長列之後照樣 ok
    #   ⚠ 而它是【2026-09-01 才開始累積】的（逐 commit 追過：列數 8→17 單調增、
    #     起點固定 2026-09-01）⇒ 九月之前我方沒有大盤法人金額
    #   ⭐ 日期取 `date` 欄（交易日）：它是我方寫進去的那一天的資料，
    #     ⇒ 停一天就停在那裡，正好量「多久沒長新的」
    #   5 天 ＝ 連假 ＋ 一次失敗（與上市停止買賣中名單同一把尺）
    ("大盤三大法人金額", os.path.join(_ROOT, "latest", "market_inst.csv"),
     "column:date", 5,
     "每個交易日一列（2026-09-01 起累積）；5 天 ＝ 連假 ＋ 一次失敗。"
     "⚠ 這一份補得回來（T86 可指定日期），守它是因為它會安靜停住："
     "寫它那一步 continue-on-error，而 crosscheck ① 只掃已有的日子"),
    # ⭐⭐ 2026-09-24 回補之後新增：大盤法人金額的【逐日檔】。
    #   ⚠ 上面那一條守的是 `latest/market_inst.csv`（2026-09-01 起 17 列），
    #     ⛔ 而回補之後真正在長的是這兩個目錄 ⇒ 兩件事，兩條守門。
    #   ⛔⛔ 為什麼不能靠 `feed_rowcount_check.py`：那一支自己會掃
    #     `data/universe/*` 全部，⚠ 但它判的是「列數對不對得上鄰近幾天」，
    #     而這兩支每天只有 4~8 列 ⇒ 它會落進「整支沒判（量太小）」那一類。
    #     ⇒ ⭐ 那一類它會大聲印出來，⛔ 但**大聲印出來不等於有人在守**。
    #   ⚠ 上市與上櫃分開守：兩邊是兩個端點、兩套列名、兩個回溯下限
    #     ⇒ 只守一邊，另一邊停掉時這裡照樣綠。
    ("上市大盤法人金額（逐日檔）",
     os.path.join(_ROOT, "universe", "instamt"), "filename", 5,
     "每個交易日一份（BFI82U，回溯下限民國 93-03-03）；"
     "5 天 ＝ 連假 ＋ 一次失敗。⚠ 這一份補得回來，守它是因為它會安靜停住"),
    ("上櫃大盤法人金額（逐日檔）",
     os.path.join(_ROOT, "universe", "otcinstamt"), "filename", 5,
     "每個交易日一份（insti/summary，回溯下限 2017-01-03）；"
     "⛔⛔ 而 2017-01-03~2018-01-11 那一段**沒有外資也沒有總計列**"
     "（本線 2026-09-24 二分量到：2018-01-15 起才有），"
     "⚠ 2018-01-12 端點回 stat=ok ＋ 0 列（重問三次一樣）⇒ 那是端點的洞"),
    ("幣市日 K（BTC 代表）", os.path.join(_ROOT, "crypto", "BTC.csv"),
     "asof_column", 3,
     "每天一趟（週末也交易，沒有連假）；3 天 ＝ 週期 1 ＋ 一次失敗 ＋ "
     "data.binance.vision 上傳延遲 1。⚠ 用 asof（我方寫入日），"
     "空跑那一趟 asof 不前進 ⇒ 量的正是『多久沒拿到新資料』"),
]


def _newest(path, how):
    """→ (日期字串, 說明)。取不到回 (None, 原因)。"""
    if how in ("filename", "filename_roc"):
        if not os.path.isdir(path):
            return None, "目錄不存在"
        # ⛔ 2026-09-09 抓到的第二句假診斷：這裡本來只收 `.csv`，
        #   而 `data/holiday/` 存的是 **`.html`**（每天一份原始公告頁）
        #   ⇒ 報告寫「天然災害停班原始頁：目錄是空的」，**那句是假的**：
        #     目錄裡有 `2026-09-09.html`，是這支不認得它的副檔名。
        #   照著報告去查，會去查 holiday.py 為什麼沒存檔——而它存了。
        #   ⇒ 認**檔名**（日期），不認副檔名。
        fs = [x for x in os.listdir(path)
              if re.match(r"^(20[0-9]{2}-[0-9]{2}-[0-9]{2}|1[0-9]{6})\.", x)]
        if not fs:
            n_any = len(os.listdir(path))
            return None, ("目錄是空的" if n_any == 0
                          else f"目錄有 {n_any} 個檔，但沒有一個的檔名是日期")
        stems = sorted(x.rsplit(".", 1)[0] for x in fs)
        s = stems[-1]
        if how == "filename_roc" and re.fullmatch(r"1[0-9]{6}", s):
            return f"{int(s[:3]) + 1911}-{s[3:5]}-{s[5:7]}", f"{len(fs)} 份"
        if re.fullmatch(r"20[0-9]{2}-[0-9]{2}-[0-9]{2}", s):
            return s, f"{len(fs)} 份"
        return None, f"檔名認不出日期：{s!r}"
    # ⭐ `asof_column` 是 `column:asof` 的別名（⛔ 既有那幾項不動）
    #   ⚠ 新增的一律寫 `column:<欄名>`：日期欄不一定叫 asof
    #     （market_inst 的是 `date` ＝ 交易日）
    if how == "asof_column" or how.startswith("column:"):
        col = "asof" if how == "asof_column" else how.split(":", 1)[1]
        if not os.path.exists(path):
            return None, "檔案不存在"
        import csv
        best = ""
        n = 0
        with io.open(path, encoding="utf-8") as f:
            rd = csv.DictReader(f)
            # ⛔ 欄名打錯會讓這一支【永遠回「沒有值」】而看起來像資料壞了
            #   ⇒ 先說清楚是欄名不在，⚠ 不是沒有值
            if rd.fieldnames is not None and col not in rd.fieldnames:
                return None, f"沒有 {col} 這一欄（表頭：{rd.fieldnames}）"
            for r in rd:
                n += 1
                v = (r.get(col) or "").strip()
                if v > best:
                    best = v
        return (best or None), (f"{n} 列" if best else f"沒有 {col} 值")
    return None, f"不認得的取法 {how}"


# ⚠ 排程觸發的區塊**幾天沒動就算壞掉**。
#   ⛔ 不可以統一用一個數字：daily.yml 天天跑、probe.yml 只在工作日跑、
#     forward.yml 一個月一次 ⇒ 一把尺量三種週期，不是誤報就是漏報。
#   ⇒ 沒有把握的一律用最寬的那個（月頻 40 天），⚠ 而**寬到失去意義**要標出來。
SCHED_TOL_DAYS = 3          # 日／週頻排程：容忍 3 天（週末 ＋ 一次失敗）
SCHED_TOL_MONTHLY = 40      # 月頻排程：容忍 40 天（週期 31 ＋ 緩衝）


def _wf_crons(root=None):
    """`.github/workflows/*.yml` 的 **workflow 名稱 → cron 清單**。→ dict。

    ⛔ 為什麼要讀 workflow：`runlog.who()` 寫的是 `GITHUB_WORKFLOW`（＝ `name:`），
    ⚠ 而「這一支多久跑一次」**只有 cron 講得準**。
    ⭐ 我第一版拿名稱裡有沒有「月」字去猜 ⇒ `股本／發行股數（每月）` 剛好中，
      ⛔ 而那是運氣：`forward.yml` 也是月頻、`capital` 改個名字就會被當成日頻
      ⇒ 那一塊會**天天紅**，然後被學會忽略（四點五那條 `feeds:margin` 的形狀）。
    """
    here = root or os.path.dirname(os.path.abspath(__file__))
    out = {}
    for p in sorted(glob.glob(os.path.join(here, ".github", "workflows", "*.yml"))):
        t = io.open(p, encoding="utf-8").read()
        m = re.search(r"^name:\s*(.+)$", t, re.M)
        if not m:
            continue
        out[m.group(1).strip().strip('"\'')] = re.findall(
            r'-\s*cron:\s*"([^"]+)"', t)
    return out


def _tol_for(crons):
    """從 cron 推容忍天數。→ (天數, 說明) 或 (None, 原因)。

    ⛔ 判準是 cron 的**日期欄**，⚠ 不是名字：
    日期欄是 `*` ⇒ 每天／每週跑；是具體日子（`1`、`13`、`2-7`）⇒ 一個月一次。
    """
    if not crons:
        return None, "這一支沒有 cron（⇒ 它不是排程跑的）"
    monthly = False
    for c in crons:
        f = c.split()
        if len(f) >= 3 and f[2] != "*":
            monthly = True
    return ((SCHED_TOL_MONTHLY, f"月頻（cron 指定了日期：{crons}）") if monthly
            else (SCHED_TOL_DAYS, f"日／週頻（cron：{crons}）"))


def _blocks(path):
    """把 `_last_run.md` 拆成 [(區塊名, 時戳字串, 那一行的其餘部分)]。

    ⛔ 只讀，不改。⚠ 舊格式的區塊沒有「觸發 …」那一段 ⇒ 第三個欄位是空的，
    而那要被讀成「**這一塊講不出它是誰寫的**」，⛔ 不是「它是手動的」。
    """
    out = []
    if not os.path.exists(path):
        return out
    name = None
    for ln in io.open(path, encoding="utf-8"):
        if ln.startswith("## "):
            name = ln[3:].split("　")[0].strip()
        elif ln.startswith("最後執行：") and name:
            body = ln[len("最後執行："):].strip()
            t = body.split("（台北）")[0].strip()
            rest = body.split("（台北）", 1)[1] if "（台北）" in body else ""
            out.append((name, t, rest))
            name = None
    return out


def stale_scheduled(rl, path=None):
    """⭐ 排程寫的區塊有沒有死掉——⛔ 而「沒人按」要跟「壞掉」分開講。

    ## ⛔ 為什麼要有這一段

    2026-09-15 掃 `_last_run.md`：**8 個區塊**停在 09-09~09-11，而同一份裡
    另外 52 個是今天的。⚠ 而那一份報表上**分不出**哪幾個是
    「該天天跑而死掉」、哪幾個是「本來就要人按、沒人按」。

    ⇒ ⭐ 判準來自區塊**自己講的**那一段（`runlog.who()`：`觸發 schedule`
    還是 `workflow_dispatch`），⛔ 不是我在這裡寫一份清單去猜——
    清單會跟 workflow 走岔，而走岔的那一天沒有人會發現（四點五）。

    ⇒ 分**三類**，⛔ 缺第三類就會把舊格式讀成「手動的」：

    ```
    ⛔ 排程 ＋ 過期     這是**壞了**             ⇒ rl.check 紅
    ⚠ 手動 ＋ 過期     只是沒人按               ⇒ info（要不要排程是另一個決定）
    ⛔ 講不出來        舊格式／不是 Actions 寫的 ⇒ info，並**明講它講不出來**
    ```
    """
    path = path or runlog.PATH
    crons = _wf_crons()
    today = datetime.now(TPE).date()
    dead, idle, mute = [], [], []
    for name, t, rest in _blocks(path):
        try:
            age = (today - datetime.fromisoformat(t).date()).days
        except ValueError:
            mute.append(f"{name}（時戳讀不懂：{t[:20]}）")
            continue
        if "觸發 " not in rest:
            mute.append(f"{name}（{age} 天前）")
        elif "觸發 schedule" in rest:
            # ⭐ 容忍度從**那一支的 cron** 推，⛔ 不是從名字猜（見 `_wf_crons`）
            wf = rest.split("｜")[2].strip() if rest.count("｜") >= 2 else ""
            tol, why_tol = _tol_for(crons.get(wf, []))
            if tol is None:
                # ⛔ 講不出週期就**不判**（⚠ 亂判會變成一塊天天紅的閘門）
                mute.append(f"{name}（排程，但 {why_tol}）")
            elif age > tol:
                dead.append(f"{name}（排程{why_tol}，{age} 天前 > 容忍 {tol}）")
        elif age > SCHED_TOL_DAYS:
            idle.append(f"{name}（手動，{age} 天前）")
    rl.info("排程區塊", f"死掉 {len(dead)}｜手動而久沒按 {len(idle)}"
                        f"｜⛔ **講不出自己是誰寫的** {len(mute)}")
    if idle:
        rl.info("⚠ 手動而久沒按（⛔ 這不是壞掉）", "；".join(sorted(idle)[:12]))
    if mute:
        # ⛔ 這一類要**大聲**：它不是「沒問題」，是「這一格量不到」。
        rl.info("⛔ 講不出自己是誰寫的（舊格式／非 Actions 寫的）",
                "；".join(sorted(mute)[:12])
                + "｜⇒ 等它們各自再被寫一次就會自己講")
    # ⭐ 只有「排程 ＋ 過期」才是紅的：那代表**該天天跑的東西死了**。
    rl.check("排程寫的區塊都還活著", not dead,
             "；".join(sorted(dead)) or "沒有排程區塊過期")
    return len(dead)


def main():
    rl = runlog.Run("freshness")
    today = datetime.now(TPE).date()
    bad = []
    for name, path, how, tol, why in TARGETS:
        d, note = _newest(path, how)
        if not d:
            rl.info(name, f"⚠ 取不到日期：{note}")
            bad.append(f"{name}（{note}）")
            continue
        age = (today - datetime.strptime(d, "%Y-%m-%d").date()).days
        flag = "" if age <= tol else "　← ⛔ **過期**"
        rl.info(name, f"最新 {d}｜{age} 天前｜容忍 {tol} 天｜{note}{flag}")
        if age > tol:
            bad.append(f"{name} 最新 {d}（{age} 天前 > 容忍 {tol}）")
    # ⛔ 這一條要真的會失敗。**這幾份的共同點是「壞掉時整條管線是綠的」**，
    #   所以只有這裡會吵——info 不夠，必須是 check。
    rl.check("「不累積就永久失去」的那幾份都還在累積", not bad,
             "；".join(bad) + "｜⛔ 這類資料補不回來，紅了要當天處理")
    rl.info("容忍天數的理由", "；".join(f"{n} {tol} 天（{why}）"
                                    for n, _p, _h, tol, why in TARGETS))
    # ⭐ 第二半：**排程寫的區塊有沒有死掉**（⛔ 跟「沒人按」分開講）
    stale_scheduled(rl)
    return rl.finish()


if __name__ == "__main__":
    sys.exit(main())

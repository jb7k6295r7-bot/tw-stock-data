# -*- coding: utf-8 -*-
"""大漲觀察月報／季加報（台股策略線 seq538「大漲觀察月報請每月自動產」，使用者 10/22 交代；回測線 1022-0030 收）——回測線開發子代理，2026-10-22。
⛔ 描述，不是選股規則：不判、不計 N、不擇優（各組照來信順序、G 照代號序，⛔ 不排名）；⛔ 不算任何「之後報酬」。
LINE（台股 seq539、情報 0030 §三／0035，使用者同意）：只推檔尾「LINE 摘要」（≤ 4 行，格式見 line_month／line_quarter；⛔ 不判、不推薦、不寫買賣、不加固定警語）。
  轉強（A～E、H；欄 up）＝ 近 3 月年增平均 ≥ 近 12 月年增平均 ＋ 5 點，或首次創 24 月新高（本期創、上一期沒創）——與前瞻小部位確認同一條件（照字面）；
    LINE「只寫有變化的」⇒ 只列本期 up 成立、上一期 up 不成立（或首次創 24 月新高）者；警訊 ＝ F 組 ①② 任一（照字面）；
  重點 ＝ 3491 單月是否 ≥ 3.9 億；季加報 ＝ 1519、1513 合約負債年增。
前瞻紀錄「長線候選確認前先小部位」seq8（446b15cd5b6be0bf；裁定 seq466 核，取代 seq5～7；候選變更依 seq462、seq466 急件；前瞻、不計 N、金額不記；LINE 只推事件行）：
  候選 SP_CANDS：1503、1513、1305、1312（起點 2026-10-22）；4510、6609、8936、3376（起點 2026-10-27；10/23 颱風休市、10/26 補假）；2002、1101、2014 已刪（未買）。
  起點＝核後下一交易日開盤 1 份（未還原開盤；無成交／開盤鎖漲停 ⇒ 買不到並寫明；本模組第一次 auto 補記）；新候選通知在起點前一個日曆日 14:00 後（＝前一晚）。
  1312、4510、6609、3376 另記「標記」列＝進場時已轉強（檢查時不當確認前樣本）。
  每份月報（鍵 ≥ 2026-11）每期照判 up（⛔ 不套 LINE 過濾）⇒ 月報隔天開盤加 2 份（只加一次，買不到也算）。
  放棄：第 i 份月報 ＝ 該檔首份判定月報起算月數 ＋ 1；第 12 份仍未轉強 ⇒ 該份月報隔天開盤賣出、記「未確認」（無成交／鎖跌停順延）；
  當期營收未公布 ⇒ 記「未判」、下一份補判上一期（up_prev）；第 12 份未公布 ⇒ 第 13 份只補判上一期、以它為放棄判定、賣出順延到該份隔天（seq447 補句）。
  新需求型 SP_NEWDEMAND（3376，seq8）：⛔ 不看營收轉強；燈2（產業判、寄信）由回測線記進 lamp2.csv ⇒ 收信後下一交易日開盤加 2 份（前一晚 LINE 通知）；
    月報判定列記「燈2已亮／燈2未亮」（營收只記）；第 12 份月報前燈2 都沒亮 ⇒ 隔天開盤賣。
  已確認：1503、1513、4510、6609、8936、3376 不設停損、不設天數；缺貨型（1305、1312）照抱，另兩個只問不賣提醒：
    ① 報價代理連 3 個月月增 < 0（sp_ppi_hits／ppi_loader：私有庫 us-stock-data 美國 PPI；設定「小部位_報價提醒」10/23 開；最新月須在進場後發布、同段只推一次）
    ② 確認那份月報資料日之後滿 250、625 個交易日各一次（seq6；附三項描述：同業擴產／復產、營收年增自確認後高點連 3 月下降、股價距確認後最高收盤）
  紀錄：backtest/forward/bigrun_monthly/smallpos.csv（照規則、只追加、已寫凍結；通知列「新候選通知」「提醒」的 LINE 原文存在 judge_detail）、
  smallpos_user.csv（使用者實際；種子＝情報 20261022-1000 成交；之後成交由回測線 --user-add 或手填同欄位補記）。auto 每晚都跑；手動 --kind 只試算不寫。
  月報段「確認前小部位前瞻」：照規則／使用者實際兩欄並列、最大回落、0050 還原同期、進場時已轉強標記、缺貨型四檔 F①F② 只記、通知紀錄。
  LINE 事件行（設定「小部位_LINE」＝true 才出；⛔ 本模組不改設定檔；⛔ 不寫報酬；不計入摘要 4 行，seq444）：
    「  小部位：代號 名稱 轉強 ⇒ 明天開盤加 2 份（約 N 股）」（N ＝ 設定「小部位」× 2 ÷ 月報資料日未還原收盤，零股取整）
    「  小部位：代號 名稱 第 12 份月報仍未轉強 ⇒ 明天開盤賣」（月報夜）
    「  小部位：代號 名稱 新候選 ⇒ 10/27（二）開盤買 1 份（約 N 股）」：以【台北今天】判（不看資料日）——起點前最後一個交易日 14:00 後、
      或之後到起點前的第一次執行出一次並記「新候選通知」列；同資料日名單重產原樣補回；別的資料日、起點後都不再出（seq458 §二、10/22 2025 修）。
    「  小部位：代號 名稱 確認後已滿 625 個交易日 ⇒ 續抱或賣？（你決定）」（到達那晚一次）
    非月報夜 ⇒ 名單另一節「## 十二、大漲觀察小部位（通知）」；月報夜 ⇒ 插進月報 LINE 摘要。
每日名單第十二節（--md）：「## 十二、大漲觀察月報（YYYY-MM 營收）」／「## 十二、大漲觀察季加報（YYYYQn）」＝ LINE 摘要 ＋ A～F 表（組標題降成 ###）；
  整節置換、接檔尾、冪等；只出現在「產出那個資料日」的名單（同資料日名單重產 ⇒ 從 <鍵>_<種類>_daily節.md 補回）；其他資料日 ⇒ 移除舊節。
⛔ 名單是事後挑的，不能拿來回測過去。名單增減：台股另寄信 ⇒ 改本檔頂端常數 GROUPS／POOL169（其他不動）。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.bigrun_monthly --sha <main sha> [--asof YYYY-MM-DD] [--out <md 路徑>] [--kind auto|月報|季加報] [--md <每日名單 md>]
    選項：--procs N（PTH 全市場平行數，預設 3）｜--g-rev pit|hist（G 表月營收口徑，預設 pit；hist ＝ 10/20 快照原口徑，只給驗證用）｜--state 路徑（測試用）
    驗證：PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.bigrun_monthly_check --csv <月報 csv> [--qcsv <季加報 csv>] [--skip-g]

到期（--kind auto；每晚 run_daily_list 跑一次，未到期 ⇒ 印「未到期」exit 0）：
  月報   ＝ 資料日所在月 ≥ 12 日、且 state.json 沒有該月（鍵 YYYY-MM；首份 2026-11）。12 日遇假日 ⇒ 12 日起第一個有資料的晚上。
  季加報 ＝ 資料日 ≥ 財報法定期限隔天（Q4 3/31、Q1 5/15、Q2 8/14、Q3 11/14 的隔天）、且 state.json 沒有該季（鍵 YYYYQn；首份 2026Q3）。
         期限隔天遇假日 ⇒ 之後第一個有資料的晚上（2026-11-15 是週日 ⇒ 資料日 11-16 才到期）。
  --kind 月報／季加報 ＝ 不看到期、照產（乾跑用）：md 寫 --out、csv 寫在 --out 旁邊，⛔ 不寫 state、不寫 forward 夾。
  auto 產出 ＝ forward/bigrun_monthly/<鍵>_<種類>.md／.csv（＋ _meta.json）；--out 有給再複製一份 md（兩種同晚到期 ⇒ 季加報那份檔名加 _季加報）。
  成功才寫 state.json；失敗 ⇒ exit 1（不影響別的流程）。產出路徑印成「產出 <種類>：<md>」一行一個。

讀法（執行者定，2026-10-22）：
 R1 版本：月營收、財報一律取「資料日 23:59:59（台北）當時的 main」＝ --sha 的 first-parent 鏈上 commit 時間 ≤ 截止的最新一個（AC）。
    ⇒ 不前視（公布到我方庫的時間 ≤ 資料日）；即時跑時 AC ＝ --sha（或更早一個）。價格用 ~/h2data/<sha>（run_daily_list 同一份唯讀 archive；沒有就照同法建）。
 R2 月營收「公告當時口徑」：每日版 data/mops/revenue/<期>.csv（OpenAPI，期別欄與資料年月須相符，錯位列丟掉）有該列 ⇒ 用它；否則 revenue_hist（AC 版）。
    年增、月增照「同一列」的去年當月、上月營收（公告當列）。revenue_hist 與每日版不同、或 _changes.log（AC 版，時戳 ≤ 截止）有當月營收更正 ⇒ 標註（照實、不改值）。
 R3 期別：月報期 ＝ 法定公告期限（次月 10 日）已過的最新一期；可用日照全線規則（2025-12 期以前次月 10 日後、2026-01 期起次月 15 日後，嚴格大於）；
    未過 ⇒ 照實寫「依可用日規則尚未可用，以已公布值描述」。個股該期未公布 ⇒ 用它最新已公布期並標註。
 R4 定義（同 10/20 169 檔快照）：近 3 月年增 ＝ 近 3 月年增平均；加速 ＝ 近 3 月年增平均 − 近 12 月年增平均；24 月新高 ＝ 當月 ≥ 前 24 月最大且前 24 月全有值（不全 ⇒ 空）。
    距一年高點、近一年漲幅、壞根旗標 ＝ researchLongPool.price_block（還原收盤、含息；窗內壞根照算只標）；收盤 ＝ 未還原。3718 價格接 5371（1:1 推定）。
 R5 季加報（fs_xbrl；合併 cr 優先）：合約負債 ＝ contract_liabilities_current ＋ _noncurrent（兩欄皆空 ⇒ 空；一欄空 ⇒ 視為該公司無此科目）；
    單季 ＝ 年初累計差分（Q1 不減）；存貨天數 ＝ 期末存貨 ÷ 單季營業成本 × 91.25；毛利率 ＝ 單季營業毛利 ÷ 單季營業收入；年變化 ＝ 本季 − 去年同季。
    營業成本、毛利、營收：fs_xbrl（cost_of_sales_ytd、gross_profit_ytd、revenue_ytd；2026-10-21 才進庫）缺 ⇒ fs_hist ci（千元 ×1000）⇒ fin_hist，
    同一來源相減、csv pl_src 欄與 md 註記來源。
    可用日 ＝ filing_dates uploaded_at（同期有 AI1 ⇒ AI1 最早；否則最早文件）≤ 資料日；無時戳的季不給值（⛔ 不退法定期限）。3718 該季自己沒有 ⇒ 用 5371。
 R6 G 表 ＝ researchLongPool（10/20 快照那支）同一批函式重產，同欄位（PTH 欄名換成當月底月份）；月營收改用 R2 公告當時口徑、期別用 R3
    （--g-rev hist ⇒ 原口徑 revenue_hist，驗證與 10/20 快照逐字相符用）。每日名單檔不在 ⇒ 名單三欄空白並註明。
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
import traceback

import numpy as np
import pandas as pd

REPO = os.path.expanduser("~/tw-p17")
sys.path.insert(0, REPO)
from backtest import researchLongPool as RLP          # noqa: E402  ⛔ 只 import（import 時 chdir ~/tw-p17、GATE_V2 開）
from backtest import data as D                        # noqa: E402

# ═════════════ 名單（台股來信 seq538；增減只改這裡） ═════════════
GROUPS = [
    ("A", "電力", [("重電", "1519 1513 1503 1514"), ("機櫃電源", "2308 2301 6282")]),       # BBU 移到 K「已漲過」（台股 seq568 §三）
    ("B", "機器人", [("", "2049 4576 2233 4583 1536 2417")]),
    ("C", "軍工衛星", [("", "3491 2313 6271 8033 2634 3718")]),
    ("D", "塑化中游", [("", "1301 1303 1326 6505 1314 1304 1305 1312 2002")]),       # 1305、1312、2002：台股 seq544（裁定 seq442）補
    ("E", "水泥", [("", "1101 1102")]),
    ("F", "缺貨型尾段警訊", [("", "2408 2344 2327 2492 6173 8358 1802 1815")]),
    ("H", "早期候選", [("", "3481 1795 4123 6550")]),                              # 台股 seq544 新增；欄位同 A～E
    ("I", "鋼鐵（先盯）", [("", "2014 2023")]),                                      # 台股 seq568 §三、產業 seq10：中鴻、燁輝（中鋼在 D）
    ("J", "先盯組（只記轉強）", [("造紙", "1909 1907 1905"), ("國防造船", "2208 6753"), ("AR 眼鏡", "3504"), ("都更", "2548 2520")]),   # 台股 seq568 §三
    ("K", "已漲過（只看警訊）", [("BBU", "6781 3211 4931"), ("", "1710 1718")]),   # 4931 新盛力：產業 seq12         # 台股 seq568 §三：BBU、東聯、中纖；欄位同 F（①②③）
]
WATCH = {"3491": 390_000}          # 千元：單月是否 ≥ 3.9 億（只標）
F_GROUP, F_DROP = "F", -0.30       # F 組另標：營收月增 ≤ 0 連 2 月、股價距一年高點 ≤ −30%（只標、不判）
WARN_GROUPS = ("F", "K")            # 只看警訊的組（①②③ 標記欄；LINE 進「警訊」）
PAPER_PPI = ("J", "造紙", "WPU091")  # 先盯組造紙：美國 PPI 造紙代理「報價年增轉正」一欄（描述；私有庫只出判定、不出值）
POOL169 = ("1303 1503 1504 1513 1514 1519 1536 1590 1597 1603 1605 1608 1609 1612 1615 1618 1623 1727 1802 1815 2049 2233 2301 2308 2313 "
           "2314 2316 2317 2327 2328 2330 2337 2344 2345 2352 2359 2360 2367 2368 2375 2382 2383 2404 2408 2417 2421 2429 2449 2454 2455 "
           "2458 2464 2467 2472 2478 2492 2630 2634 2645 3006 3008 3013 3017 3019 3026 3037 3044 3081 3090 3105 3131 3138 3163 3167 3189 "
           "3211 3227 3260 3289 3323 3324 3357 3363 3402 3406 3413 3443 3450 3491 3583 3587 3624 3653 3661 3680 3711 3718 4573 4576 4583 "
           "4755 4772 4908 4916 4919 4931 4958 4967 4971 4976 4977 4979 4989 4991 5289 5292 5340 5475 5536 6139 6173 6175 6187 6196 6213 "
           "6223 6239 6271 6274 6282 6285 6442 6449 6451 6510 6515 6526 6613 6640 6667 6669 6672 6683 6691 6781 6805 6826 6830 6862 6903 "
           "6933 6944 6959 7402 7556 7728 7734 7769 8033 8038 8043 8046 8110 8150 8210 8222 8299 8358 8996").split()
SPLICE = {"3718": "5371"}
FIRST = {"月報": "2026-11", "季加報": "2026Q3"}
FS_DEADLINE = {1: (5, 15), 2: (8, 14), 3: (11, 14), 4: (3, 31)}     # Q4 ＝ 隔年 3/31
QWATCH = ["1519", "1513"]           # 季加報 LINE 重點：合約負債年增
ACC_UP = 0.05                       # LINE 轉強：近 3 月年增平均 ≥ 近 12 月年增平均 ＋ 5 點（本期才達成、上一期未達）
SEC_PREFIX = "## 十二、大漲觀察"      # 每日名單第十二節（月報／季加報）
DESC = "描述，不是選股規則。⛔ 不判、不計 N、不擇優（各組照台股來信順序、不排名）；LINE 只推檔尾摘要；名單是事後挑的，不能拿來回測過去。"

FWD = os.path.join(REPO, "backtest", "forward", "bigrun_monthly")
STATE = os.path.join(FWD, "state.json")
WORK = os.path.expanduser("~/bigrunwork")
H2 = os.path.expanduser("~/h2data")
SNAP_PATHS = ["data/adj", "data/meta", "data/mops/revenue_hist", "data/stocks", "data/stocks_per"]   # = run_daily_list.sh
REV_PATHS = ["data/mops/revenue", "data/mops/revenue_hist", "data/mops/_changes.log"]
TZ = "Asia/Taipei"
DAYS_Q = 91.25
LISTS = ("營飆v1已達成", "營量v1已達成", "營量v1即將達成")


def log(s):
    print(f"[{pd.Timestamp.now(tz=TZ).strftime('%H:%M:%S')}] {s}", flush=True)


def af_codes():
    out = []
    for g, gname, subs in GROUPS:
        for sub, cs in subs:
            out += [(g, gname, sub, c) for c in cs.split()]
    return out


# ═════════════ 到期 ═════════════
def fs_deadline(y, q):
    m, d = FS_DEADLINE[q]
    return pd.Timestamp(y + 1 if q == 4 else y, m, d)


def quarter_key(asof):
    """資料日當下『最近一個已過期限隔天』的季（YYYYQn）；沒有 ⇒ None。"""
    best = None
    for y in (asof.year - 2, asof.year - 1, asof.year):
        for q in (1, 2, 3, 4):
            d1 = fs_deadline(y, q) + pd.Timedelta(days=1)
            if d1 <= asof and (best is None or d1 > best[0]):
                best = (d1, f"{y}Q{q}")
    return best[1] if best else None


def due(asof, state):
    """回 [(種類, 鍵)]；state ＝ {"月報": {鍵: …}, "季加報": {鍵: …}}。"""
    out = []
    mk = asof.strftime("%Y-%m")
    if asof.day >= 12 and mk >= FIRST["月報"] and mk not in state.get("月報", {}):
        out.append(("月報", mk))
    qk = quarter_key(asof)
    if qk and qk >= FIRST["季加報"] and qk not in state.get("季加報", {}):
        out.append(("季加報", qk))
    return out


def load_state(p):
    if os.path.exists(p):
        return json.load(open(p, encoding="utf-8"))
    return {"月報": {}, "季加報": {}}


def save_state(p, st):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    tmp = p + ".tmp"
    json.dump(st, open(tmp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    os.replace(tmp, p)


# ═════════════ 資料版本 ═════════════
def git(*a):
    r = subprocess.run(["git", "-C", REPO, *a], capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError(f"git {' '.join(a[:2])} 失敗：{r.stderr.strip()[-300:]}")
    return r.stdout


def cutoff_of(asof):
    return pd.Timestamp(f"{asof.date()} 23:59:59", tz=TZ)


def asof_commit(sha, asof):
    """main 在資料日 23:59:59（台北）當時的版本：sha 的 first-parent 鏈上 commit 時間 ≤ 截止的最新一個。"""
    cut = cutoff_of(asof)
    L = git("rev-list", "--first-parent", "--format=%cI", sha).splitlines()
    for i in range(0, len(L) - 1, 2):
        h = L[i].split()[1]; t = pd.Timestamp(L[i + 1]).tz_convert(TZ)
        if t <= cut:
            return h, t
    raise RuntimeError(f"{sha[:10]} 的 first-parent 鏈上沒有 ≤ {cut} 的 commit")


def _archive(commit, paths, root):
    tmp = root + ".tmp"
    subprocess.run(["rm", "-rf", tmp], check=True); os.makedirs(tmp)
    ar = subprocess.Popen(["git", "-C", REPO, "archive", commit] + paths, stdout=subprocess.PIPE)
    subprocess.run(["tar", "-x", "-C", tmp], stdin=ar.stdout, check=True)
    if ar.wait() != 0:
        raise RuntimeError(f"git archive {commit[:10]} 失敗")
    return tmp


def ensure_snapshot(sha):
    """價格快照 ~/h2data/<sha>/data（run_daily_list.sh 同一份；沒有就照同法：依 data 子樹 tree id 存 daily_<key>，<sha> 放 symlink）。"""
    link = os.path.join(H2, sha)
    if os.path.isdir(os.path.join(link, "data", "stocks")):
        return os.path.join(link, "data")
    key = hashlib.sha1(("\n".join(git("rev-parse", f"{sha}:{p}").strip() for p in SNAP_PATHS) + "\n").encode()).hexdigest()[:16]
    dk = os.path.join(H2, f"daily_{key}")
    if not os.path.isdir(os.path.join(dk, "data", "stocks")):
        t0 = time.time()
        tmp = _archive(sha, SNAP_PATHS, dk)
        subprocess.run(["rm", "-rf", dk], check=True); os.replace(tmp, dk)
        subprocess.run(["chmod", "-R", "a-w", dk], check=True)
        log(f"[快照] 建 {dk}（{time.time() - t0:.0f}s）")
    if not os.path.lexists(link):
        os.symlink(dk, link)
    return os.path.join(dk, "data")


def ensure_rev(commit):
    root = os.path.join(WORK, f"rev_{commit[:10]}")
    if os.path.isdir(os.path.join(root, "data", "mops", "revenue_hist")):
        return os.path.join(root, "data", "mops")
    paths = [p for p in REV_PATHS if subprocess.run(["git", "-C", REPO, "cat-file", "-e", f"{commit}:{p}"]).returncode == 0]
    tmp = _archive(commit, paths, root)
    subprocess.run(["rm", "-rf", root], check=True); os.replace(tmp, root)
    return os.path.join(root, "data", "mops")


FUND_NOTES: list = []


def ensure_fund(commit, sha=None):
    """財報 archive（filing_dates、fs_xbrl、fs_hist、fin_hist ＝ researchLongPool.FUND_PATHS）取截止版本 commit；
    某路徑在截止版本還不存在（例：fs_xbrl 2026-10-15 才進 main；只有回補舊資料日才會碰到）⇒ 該路徑改取 sha 版本並記 ⚠（可用日仍照上傳時戳）。"""
    os.makedirs(WORK, exist_ok=True)
    root = os.path.join(WORK, f"fund_{commit[:10]}")
    note_p = os.path.join(root, "_notes.json")
    if all(os.path.exists(os.path.join(root, p)) for p in RLP.FUND_PATHS):
        FUND_NOTES[:] = json.load(open(note_p, encoding="utf-8")) if os.path.exists(note_p) else []
        return os.path.join(root, "data")
    groups, notes = {}, []
    for p in RLP.FUND_PATHS:
        c = commit
        if subprocess.run(["git", "-C", REPO, "cat-file", "-e", f"{commit}:{p}"]).returncode != 0:
            if not sha:
                raise RuntimeError(f"截止版本 {commit[:10]} 沒有 {p}")
            c = sha; notes.append(f"{p} 在截止版本 {commit[:10]} 尚未進庫 ⇒ 用 {sha[:10]} 版本（可用日仍照上傳時戳）")
        groups.setdefault(c, []).append(p)
    tmp = root + ".tmp"
    subprocess.run(["rm", "-rf", tmp], check=True); os.makedirs(tmp)
    for c, ps in groups.items():
        ar = subprocess.Popen(["git", "-C", REPO, "archive", c] + ps, stdout=subprocess.PIPE)
        subprocess.run(["tar", "-x", "-C", tmp], stdin=ar.stdout, check=True)
        if ar.wait() != 0:
            raise RuntimeError(f"git archive {c[:10]} 失敗")
    json.dump(notes, open(os.path.join(tmp, "_notes.json"), "w", encoding="utf-8"), ensure_ascii=False)
    subprocess.run(["rm", "-rf", root], check=True); os.replace(tmp, root)
    FUND_NOTES[:] = notes
    return os.path.join(root, "data")


# ═════════════ 月營收（公告當時口徑） ═════════════
def roc(p):
    return str((int(p[:4]) - 1911) * 100 + int(p[5:]))


def pub10(p):
    """法定公告期限（次月 10 日）。"""
    y, m = int(p[:4]), int(p[5:])
    return pd.Timestamp(y + (m == 12), 1 if m == 12 else m + 1, 10)


_RULE_AVAIL = RLP.rev_avail          # 全線規則：2025-12 期以前次月 10 日、2026-01 期起次月 15 日（嚴格大於才可用）；import 時先存（build_g 會換掉 RLP 的）
_ORIG_LISTS = RLP.daily_lists
_MISS_LISTS: list = []


def rev_avail(p):
    return _RULE_AVAIL(p)


def _lists_tolerant(a):
    """每日名單檔不在 ⇒ 名單三欄空（不中止）；在 ⇒ researchLongPool.daily_lists 原樣。"""
    f = f"backtest/resultsDaily/daily_{a.date()}.md"
    if not os.path.exists(f):
        _MISS_LISTS.append(f)
        return {k: set() for k in LISTS}, None
    return _ORIG_LISTS(a)


def T(v):
    return isinstance(v, (bool, np.bool_)) and bool(v)


def Fz(v):
    return isinstance(v, (bool, np.bool_)) and not bool(v)


def load_rev_pit(MD):
    """回長表 stock_id, period, rev, prev, ly, src, h_rev, d_rev, industry（千元）＋ 診斷。"""
    H = []
    for f in sorted(glob.glob(os.path.join(MD, "revenue_hist", "*.csv"))):
        x = pd.read_csv(f, dtype=str, usecols=["stock_id", "period", "當月營收", "上月營收", "去年當月營收", "產業別"])
        H.append(x)
    h = pd.concat(H).drop_duplicates(["stock_id", "period"], keep="last")      # 檔名序 esb→tpex→twse，同 research34
    h = h.rename(columns={"當月營收": "h_rev", "上月營收": "h_prev", "去年當月營收": "h_ly", "產業別": "h_ind"})
    Dl = []; dropped = {}
    for f in sorted(glob.glob(os.path.join(MD, "revenue", "*.csv"))):
        b = os.path.basename(f)[:-4]
        if not re.fullmatch(r"\d{4}-\d{2}", b):
            continue                                                            # _esb 不用（興櫃走 revenue_hist）
        x = pd.read_csv(f, dtype=str)
        ok = x["資料年月"].astype(str).str.strip() == roc(b)
        if "period" in x.columns:
            ok &= x["period"].astype(str) == b
        if (~ok).sum():
            dropped[b] = int((~ok).sum())
        x = x[ok]
        Dl.append(pd.DataFrame({"stock_id": x["stock_id"], "period": b, "d_rev": x["營業收入-當月營收"],
                                "d_prev": x["營業收入-上月營收"], "d_ly": x["營業收入-去年當月營收"], "d_ind": x["產業別"]}))
    d = pd.concat(Dl).drop_duplicates(["stock_id", "period"], keep="last") if Dl else pd.DataFrame(columns=["stock_id", "period", "d_rev", "d_prev", "d_ly", "d_ind"])
    L = h.merge(d, on=["stock_id", "period"], how="outer")
    for c in ("h_rev", "h_prev", "h_ly", "d_rev", "d_prev", "d_ly"):
        L[c] = pd.to_numeric(L[c], errors="coerce")
    use_d = L["d_rev"].notna()
    L["rev"] = np.where(use_d, L["d_rev"], L["h_rev"])
    L["prev"] = np.where(use_d, L["d_prev"], L["h_prev"])
    L["ly"] = np.where(use_d, L["d_ly"], L["h_ly"])
    L["src"] = np.where(use_d, "每日版", np.where(L["h_rev"].notna(), "revenue_hist", ""))
    L["industry"] = L["d_ind"].fillna(L["h_ind"])
    L = L[L["rev"].notna() | L["ly"].notna()].reset_index(drop=True)
    return L, {"每日版期別": sorted(d["period"].unique().tolist()), "每日版錯位列（丟掉）": dropped,
               "revenue_hist 期別": f"{h['period'].min()}～{h['period'].max()}"}


def load_corrections(MD, codes, cut):
    """_changes.log（AC 版）裡 revenue／revenue_hist 的『當月營收』改值，時戳 ≤ 截止；錯位雜訊（資料年月、market 欄一起變）不算。"""
    p = os.path.join(MD, "_changes.log")
    out = {}
    if not os.path.exists(p):
        return out
    for line in open(p, encoding="utf-8"):
        a = line.rstrip("\n").split("\t")
        if len(a) < 4 or a[2] not in codes:
            continue
        m = re.match(r"(revenue|revenue_hist)/(\d{4}-\d{2})(?:_\w+)?\.csv$", a[1])
        if not m or "資料年月:" in a[3] or "market:" in a[3]:
            continue
        mm = re.search(r"(?:^|; )(?:營業收入-)?當月營收: ([\d.\-]+)→([\d.\-]+)", a[3])
        if not mm or pd.Timestamp(a[0]) > cut:
            continue
        out.setdefault((a[2], m.group(2)), []).append(f"{a[0][:10]} {'每日版' if m.group(1) == 'revenue' else 'revenue_hist'} {mm.group(1)}→{mm.group(2)}")
    return out


class R34Shim:
    """給 researchLongPool.revenue_block 用：load_revenue() 回公告當時口徑（同 research34.load_revenue 形狀）。"""
    def __init__(self, L):
        self.L = L

    def load_revenue(self):
        L = self.L
        rev = L.pivot(index="period", columns="stock_id", values="rev").sort_index()
        rly = L.pivot(index="period", columns="stock_id", values="ly").reindex(rev.index)
        return rev, rly, L.groupby("stock_id")["industry"].last()


def report_period(L, asof):
    ps = sorted(p for p in L["period"].unique() if pub10(p) < asof)
    return ps[-1]


def rev_metrics(L, codes, asof, corr):
    P = report_period(L, asof)
    allp = pd.period_range("2010-01", P, freq="M").astype(str)
    sub = L[L["stock_id"].isin(codes)]
    piv = {c: sub.pivot(index="period", columns="stock_id", values=c).reindex(allp) for c in ("rev", "prev", "ly", "h_rev", "d_rev")}
    srcp = sub.pivot(index="period", columns="stock_id", values="src").reindex(allp)
    out = {}
    for sid in codes:
        r = {"rev_period": "", "notes": []}
        if sid not in piv["rev"].columns:
            r["notes"].append("我方月營收庫無此代號"); out[sid] = r; continue
        rv = piv["rev"][sid]; pv = piv["prev"][sid]; ly = piv["ly"][sid]
        fin = rv[rv.notna()]
        if fin.empty:
            r["notes"].append("我方月營收庫無此代號"); out[sid] = r; continue
        last = fin.index[-1]; k = list(allp).index(last)
        if last != P:
            r["notes"].append(f"{P} 期截至資料日我方庫尚無此列（未公布或庫還沒抓到）⇒ 用我方庫最新一期 {last}")
        yoy = (rv / ly.where(ly > 0) - 1); mom = (rv / pv.where(pv > 0) - 1)
        y3 = yoy.iloc[k - 2:k + 1]; y12 = yoy.iloc[k - 11:k + 1]
        hist = rv.iloc[k - 24:k]
        r.update(rev_period=last, rev_k=rv.iloc[k], yoy=yoy.iloc[k], mom=mom.iloc[k], mom_prev=mom.iloc[k - 1],
                 yoy3=y3.mean() if y3.notna().all() else np.nan, yoy12=y12.mean() if y12.notna().all() else np.nan,
                 hi24=(bool(rv.iloc[k] >= hist.max()) if (len(hist) == 24 and hist.notna().all()) else np.nan),
                 rev_src=srcp[sid].iloc[k], rule_avail=bool(rev_avail(last) < asof), rule_avail_date=str(rev_avail(last).date()))
        r["accel"] = r["yoy3"] - r["yoy12"] if np.isfinite(r["yoy3"]) and np.isfinite(r["yoy12"]) else np.nan
        # 上一期（給 LINE 摘要「上月」與「首次創 24 月新高」）
        y3p = yoy.iloc[k - 3:k]; histp = rv.iloc[k - 25:k - 1]
        r["yoy3_prev"] = y3p.mean() if y3p.notna().all() else np.nan
        y12p = yoy.iloc[k - 12:k]
        r["accel_prev"] = r["yoy3_prev"] - y12p.mean() if (np.isfinite(r["yoy3_prev"]) and y12p.notna().all()) else np.nan
        def hi_at(j):
            h = rv.iloc[j - 24:j]
            return bool(rv.iloc[j] >= h.max()) if (np.isfinite(rv.iloc[j]) and len(h) == 24 and h.notna().all()) else np.nan
        r["hi24_prev"] = hi_at(k - 1); r["hi24_prev2"] = hi_at(k - 2)
        # 轉強（LINE 摘要與前瞻 seq1 確認同一條件，照字面）：近 3 月年增平均 ≥ 近 12 月 ＋ 5 點，或首次創 24 月新高（本期創、上一期沒創）
        r["up"] = bool((np.isfinite(r["accel"]) and r["accel"] >= ACC_UP) or (T(r["hi24"]) and not T(r["hi24_prev"])))
        r["up_prev"] = bool((np.isfinite(r["accel_prev"]) and r["accel_prev"] >= ACC_UP) or (T(r["hi24_prev"]) and not T(r["hi24_prev2"])))
        r["flag_mom2"] = (bool(r["mom"] <= 0 and r["mom_prev"] <= 0) if np.isfinite(r["mom"]) and np.isfinite(r["mom_prev"]) else np.nan)
        # ③ 營收年增從高點連 3 月下降（台股 seq568 §三，警訊只描述）★ 讀法：k−3 那期年增是近 12 期（k−11～k）最高，之後 k−2、k−1、k 逐期下降；12 期須全有值
        y12w = yoy.iloc[k - 11:k + 1]
        r["flag_yoy3dn"] = (bool(y12w.iloc[-4] >= y12w.max() and y12w.iloc[-3] < y12w.iloc[-4] and y12w.iloc[-2] < y12w.iloc[-3] and y12w.iloc[-1] < y12w.iloc[-2])
                            if len(y12w) == 12 and y12w.notna().all() else np.nan)
        if not np.isfinite(r["yoy12"]):
            r["notes"].append(f"近 12 月年增有缺 {int(y12.isna().sum())} 個月（加速、近 12 月空）")
        if not (len(hist) == 24 and hist.notna().all()):
            r["notes"].append(f"前 24 月不全（缺 {int(hist.isna().sum())} 個月）⇒ 24 月新高不判")
        if sid in WATCH:
            r["flag_watch"] = bool(rv.iloc[k] >= WATCH[sid])
        # 更正標註（窗內 15 期）
        cs = []
        for p in allp[max(0, k - 14):k + 1]:
            hv, dv = piv["h_rev"][sid].get(p), piv["d_rev"][sid].get(p)
            if pd.notna(hv) and pd.notna(dv) and hv != dv:
                cs.append(f"{p} 每日版（公告）{dv:,.0f} vs revenue_hist {hv:,.0f} 千元")
            for c in corr.get((sid, p), []):
                cs.append(f"{p} 更正 {c}")
        r["corrections"] = "；".join(cs)
        out[sid] = r
    return out, P


# ═════════════ 季加報（fs_xbrl） ═════════════
def qk_of(p):
    return int(p[:4]) * 4 + int(p[-1]) - 1


def qlabel(k):
    return f"{k // 4}Q{k % 4 + 1}"


def load_xbrl(FD, years):
    cols = ["period", "stock_id", "report", "inventories", "contract_liabilities_current", "contract_liabilities_noncurrent",
            "revenue_ytd", "cost_of_sales_ytd", "gross_profit_ytd"]
    L = []
    for y in years:
        f = os.path.join(FD, "meta", "fs_xbrl", f"fs_xbrl_{y}.csv")
        if os.path.exists(f):
            x = pd.read_csv(f, dtype={"stock_id": str}, usecols=lambda c: c in cols)
            for c in cols:                          # 營業成本、毛利三欄 2026-10-21 才進 fs_xbrl；舊版本沒有 ⇒ 空（之後退 fs_hist／fin_hist）
                if c not in x.columns:
                    x[c] = np.nan
            L.append(x)
    X = pd.concat(L)
    X["_r"] = (X["report"] != "cr").astype(int)
    X = X.sort_values(["stock_id", "period", "_r"]).drop_duplicates(["stock_id", "period"], keep="first")
    X["qk"] = [qk_of(p) for p in X["period"]]
    for c in cols[3:]:
        X[c] = pd.to_numeric(X[c], errors="coerce")
    return {s: g.set_index("qk").sort_index() for s, g in X.groupby("stock_id")}


def fs_metrics(FD, codes, asof, qkey):
    fmin, fsrc = RLP.load_filing(FD)
    lim = asof + pd.Timedelta(days=1)                       # uploaded_at ＜ 資料日隔天 00:00 ⇔ ≤ 資料日
    XB = load_xbrl(FD, range(asof.year - 3, asof.year + 1))
    want = qk_of(qkey)
    ids = sorted(set(codes) | set(SPLICE.values()))
    FS = RLP.load_fs(FD, ids, want - 9, want)              # 退路一：fs_hist ci（千元 ×1000，年初累計）
    FN = RLP.load_fin(FD, ids, want - 9, want)             # 退路二：fin_hist（rev_ytd、gp_ytd，元）
    out = {}
    for sid in codes:
        r = {"notes": []}
        used = set()
        def sid_for(k):
            if sid in SPLICE and not ((sid, k) in fmin and sid in XB and k in XB[sid].index):
                return SPLICE[sid]
            return sid

        def ok(k):
            s = sid_for(k); d = fmin.get((s, k))
            return d is not None and d < lim and s in XB and k in XB[s].index

        def val(k, c):
            s = sid_for(k)
            return XB[s][c].get(k, np.nan) if s in XB else np.nan

        def ytd_src(k, c, src):
            s = sid_for(k)
            if src == "fs_xbrl":
                return val(k, c)
            if src == "fs_hist":
                fs = FS.get(s)
                if fs is None:
                    return np.nan
                col = {"cost_of_sales_ytd": "營業成本", "revenue_ytd": "營業收入"}.get(c)
                if col is None:
                    col = "營業毛利（毛損）淨額" if fs["營業毛利（毛損）淨額"].notna().any() else "營業毛利（毛損）"
                return fs[col].get(k, np.nan)
            fn = FN.get(s)
            if fn is None:
                return np.nan
            rv, gp = fn["rev_ytd"].get(k, np.nan), fn["gp_ytd"].get(k, np.nan)
            return {"revenue_ytd": rv, "gross_profit_ytd": gp, "cost_of_sales_ytd": rv - gp}[c]

        def single(k, c):
            """單季 ＝ 年初累計差分（Q1 不減）；fs_xbrl 沒有 ⇒ fs_hist ⇒ fin_hist（同一來源相減）。"""
            for src in ("fs_xbrl", "fs_hist", "fin_hist"):
                v = ytd_src(k, c, src)
                if k % 4 != 0:
                    pv = ytd_src(k - 1, c, src)
                    v = v - pv if np.isfinite(v) and np.isfinite(pv) else np.nan
                if np.isfinite(v):
                    used.add(src)
                    return v
            return np.nan

        cand = [k for k in range(want - 8, want + 1) if ok(k)]
        if not cand:
            r["notes"].append("近 9 季皆無可用財報（無時戳或 fs_xbrl 無列）"); out[sid] = r; continue
        k = max(cand); s = sid_for(k)
        if k < want:
            d = fmin.get((sid_for(want), want))
            r["notes"].append(f"{qkey} " + (f"已上傳（{d}）但 fs_xbrl 尚無該季" if d is not None and d < lim else "截至資料日未上傳（filing_dates 無時戳）")
                              + f" ⇒ 用 {qlabel(k)}")
        if s != sid:
            r["notes"].append(f"財報用 {s}（{sid} 接續）")
        r["fs_q"] = qlabel(k); r["fs_avail"] = f"{fmin[(s, k)]}（{fsrc[(s, k)]}）"
        def cl(k_):
            a, b = val(k_, "contract_liabilities_current"), val(k_, "contract_liabilities_noncurrent")
            return np.nan if not (np.isfinite(a) or np.isfinite(b)) else np.nansum([a, b])

        def days(k_):
            iv, cg = val(k_, "inventories"), single(k_, "cost_of_sales_ytd")
            return iv / cg * DAYS_Q if np.isfinite(iv) and np.isfinite(cg) and cg > 0 else np.nan

        def gm(k_):
            gp, rv = single(k_, "gross_profit_ytd"), single(k_, "revenue_ytd")
            return gp / rv if np.isfinite(gp) and np.isfinite(rv) and rv > 0 else np.nan
        k4 = k - 4; ok4 = ok(k4)
        r["cl"] = cl(k); r["cl_ly"] = cl(k4) if ok4 else np.nan
        r["cl_yoy"] = r["cl"] / r["cl_ly"] - 1 if np.isfinite(r["cl"]) and np.isfinite(r["cl_ly"]) and r["cl_ly"] > 0 else np.nan
        r["inv"] = val(k, "inventories"); r["cogs_q"] = single(k, "cost_of_sales_ytd")
        r["inv_days"] = days(k); r["inv_days_ly"] = days(k4) if ok4 else np.nan
        r["inv_days_chg"] = r["inv_days"] - r["inv_days_ly"]
        r["gm"] = gm(k); r["gm_ly"] = gm(k4) if ok4 else np.nan
        r["gm_chg"] = r["gm"] - r["gm_ly"]
        r["pl_src"] = "、".join(x for x in ("fs_xbrl", "fs_hist", "fin_hist") if x in used)
        if used - {"fs_xbrl"}:
            r["notes"].append(f"營業成本／毛利／營收 fs_xbrl 缺 ⇒ 部分用 {r['pl_src']}")
        if not ok4:
            r["notes"].append(f"去年同季 {qlabel(k4)} 無可用財報 ⇒ 年變化空")
        if not np.isfinite(r["cl"]):
            r["notes"].append("fs_xbrl 無合約負債科目（空白≠0）")
        if not np.isfinite(r["inv"]):
            r["notes"].append("fs_xbrl 無存貨科目（空白≠0）")
        out[sid] = r
    return out


# ═════════════ G 表（researchLongPool 同一批函式） ═════════════
def build_g(asof, cal, H, FD, procs, L):
    codes = POOL169
    D.DATA = H; RLP.H = H
    r34_orig = RLP.R34
    if L is not None:
        RLP.rev_avail = pub10                 # 期別：法定期限已過（R3）；可用日規則未過者在 md 註明
        RLP.R34 = R34Shim(L)
    RLP.daily_lists = _lists_tolerant
    del _MISS_LISTS[:]
    st =pd.read_csv(os.path.join(H, "meta", "stocks.csv"), dtype=str).set_index("stock_id")
    mk = st["market"].to_dict(); nm = st["name"].to_dict()
    R1, M13, m1 = RLP.revenue_block(codes, asof)
    R2, QK, m2 = RLP.fin_block(codes, asof, FD)
    pth, pinfo, cut = RLP.pth_market(cal, procs)
    R3, m3, lists = RLP.price_block(codes, mk, asof, cal, pth)
    rows = []
    for sid in codes:
        r = {"stock_id": sid, "name": nm[sid], "market": mk[sid], "industry": R1[sid].get("industry", ""),
             "ky": "KY" in nm[sid], "first_seen": st.at[sid, "first_seen"], "data_date": str(asof.date())}
        if sid in SPLICE:
            r["note"] = "3718 2026-09-03 掛牌；價格、季報、本益比接 5371（1:1 推定）；月營收 5371 我方 0 列 ⇒ 接不上"
        r.update(R1[sid]); r.update(R2[sid]); r.update(R3[sid])
        rows.append(r)
    df = pd.DataFrame(rows)
    pcol = f"pth_{pinfo['月底'][:7]}"
    df = df.rename(columns={"pth_2026-09": pcol})
    lead = ["stock_id", "name", "market", "industry", "ky", "first_seen", "data_date", "note"]
    revc = [f"{x}_{p}" for p in M13 for x in ("rev", "yoy", "hi24")] + ["rev_accel", "rev_first"]
    fsc = [f"{x}_{RLP.qlabel(k)}" for k in QK for x in ("inv_days", "gm", "inv", "cogs", "fs_avail")] + ["fs_src", "fs_quarters_no_ts", "eps4q", "eps4q_quarters"]
    pxc = ["close_adj", "last_trade", "traded_today", "high_52w_adj", "pct_from_52w_high", "w52_badbar", "listed_lt_52w", pcol, "pth_status", "pth_top30",
           "per", "per_pct5y", "per_5y_days", "per_5y_from", "per_eps4q_own", "ret_1y", "ret_1y_base_date", "ret_1y_badbar",
           "vol20_lots", "vol20_ge500", *LISTS, "px_note"]
    raw_close = {}
    for sid in codes:
        if mk[sid] == "emerging":
            continue
        x = pd.read_csv(os.path.join(H, "stocks", f"{sid}.csv"), usecols=["date", "close"]).dropna()
        x = x[pd.to_datetime(x["date"]) <= asof]
        raw_close[sid] = float(x["close"].iloc[-1])
    df["per_eps4q_own"] = [raw_close[s] / e if (s in raw_close and np.isfinite(e) and e > 0) else np.nan for s, e in zip(df["stock_id"], df["eps4q"])]
    for c in lead + revc + fsc + pxc:
        if c not in df.columns:
            df[c] = np.nan
    df = df[lead + revc + fsc + pxc]
    miss_lists = list(_MISS_LISTS)
    if miss_lists:
        for c in LISTS:
            df[c] = np.nan
    ms = pd.DataFrame(m1 + m2 + m3, columns=["stock_id", "field", "reason"])
    ms.insert(1, "name", ms["stock_id"].map(nm)); ms.insert(2, "market", ms["stock_id"].map(mk))
    ms = ms.drop_duplicates().sort_values(["stock_id", "field"]).reset_index(drop=True)
    RLP.rev_avail = _RULE_AVAIL; RLP.R34 = r34_orig
    return dict(df=df, missing=ms, M13=M13, QK=QK, pinfo=pinfo, pcol=pcol, pth=pth, mk=mk, nm=nm, lists_missing=miss_lists, lists=lists)


# ═════════════ 排版 ═════════════
def fpct(v, pp=False):
    if v is None or not np.isfinite(v):
        return "—"
    x = v * 100
    s = f"{x:+.1f}" if abs(x) < 10 else f"{x:+.0f}"
    return s + ("pp" if pp else "%")


def fyi(v):            # 千元 → 億
    if v is None or not np.isfinite(v):
        return "—"
    y = v / 1e5
    return f"{y:.2f}" if abs(y) < 10 else (f"{y:.1f}" if abs(y) < 100 else f"{y:,.0f}")


def fyuan_yi(v):       # 元 → 億
    return fyi(v / 1000) if v is not None and np.isfinite(v) else "—"


def fpx(v):
    if v is None or not np.isfinite(v):
        return "—"
    return f"{v:,.2f}" if v < 100 else (f"{v:,.1f}" if v < 1000 else f"{v:,.0f}")


def fnum(v, nd=0):
    return "—" if v is None or not np.isfinite(v) else f"{v:,.{nd}f}"


def fbool(v, t="★", f=""):
    return "?" if v is None or (isinstance(v, float) and np.isnan(v)) else (t if bool(v) else f)


def head_lines(kind, key, asof, sha, ac, act, extra):
    return [f"# 大漲觀察{kind} {key}（資料日 {asof.date()}）", "", f"> {DESC}", "",
            f"- 資料：tw-stock-data main `{sha[:10]}`；月營收、財報取資料日 23:59（台北）當時的 main `{ac[:10]}`（commit {act.strftime('%m-%d %H:%M')}）⇒ 不前視",
            *[f"- ⚠ {x}" for x in FUND_NOTES], *extra]


def raw_close(H, sid, asof):
    p = os.path.join(H, "stocks", f"{sid}.csv")
    x = pd.read_csv(p, usecols=["date", "close"]).dropna()
    x = x[(pd.to_datetime(x["date"]) <= asof) & (x["close"] > 0)]
    return (float(x["close"].iloc[-1]), x["date"].iloc[-1]) if len(x) else (np.nan, "")


def month_report(asof, sha, ac, act, H, L, ldiag, corr, G, cal, key):
    AF = af_codes(); codes = [c for _, _, _, c in AF]
    RM, P = rev_metrics(L, codes, asof, corr)
    R3, _, _ = RLP.price_block(codes, G["mk"], asof, cal, G["pth"])
    rows = []
    for g, gname, sub, sid in AF:
        r = {"group": g, "group_name": gname, "subgroup": sub, "stock_id": sid, "name": G["nm"].get(sid, "")}
        rm = RM[sid]; px = R3[sid]
        r.update({k: v for k, v in rm.items() if k != "notes"})
        cl, cd = raw_close(H, sid, asof)
        r.update(close=cl, close_date=cd, close_adj=px.get("close_adj", np.nan), high_52w_adj=px.get("high_52w_adj", np.nan),
                 pct_from_high=px.get("pct_from_52w_high", np.nan), ret_1y=px.get("ret_1y", np.nan), ret_1y_base_date=px.get("ret_1y_base_date", ""),
                 w52_badbar=px.get("w52_badbar", ""), ret_1y_badbar=px.get("ret_1y_badbar", ""), px_note=px.get("px_note", ""))
        notes = list(rm["notes"])
        if g in WARN_GROUPS:
            r["flag_drop30"] = bool(r["pct_from_high"] <= F_DROP) if np.isfinite(r["pct_from_high"]) else np.nan
        if r.get("px_note"):
            notes.append(f"價格{r['px_note']}")
        bb = sorted(set(x for x in (str(r["w52_badbar"] or ""), str(r["ret_1y_badbar"] or "")) for x in x.split("、") if x and x != "nan"))
        if bb:
            notes.append(f"一年窗內壞根 {'、'.join(bb)}（照算、只標）")
        if sid in SPLICE:
            notes.append(f"月營收：我方 {SPLICE[sid]} 0 列 ⇒ 接不上，只有 {sid} 自身月份（年增等照實空白）")
        if cd and str(cd) != str(asof.date()):
            notes.append(f"資料日無成交，收盤用 {cd}")
        r["notes"] = "；".join(notes)
        rows.append(r)
    df = pd.DataFrame(rows)
    # ── md
    ra = rev_avail(P)
    avail_ok = ra < asof
    ex = [f"- 月營收期別：**{P}**｜全線可用日規則：{P} 期 {ra.date()} 之後可用 ⇒ " +
          ("資料日已過，可用" if avail_ok else f"⚠ **依可用日規則尚未可用，以已公布值描述**（公告當時口徑）"),
          f"- 月營收來源：每日版（OpenAPI，{('、'.join(ldiag['每日版期別'][-3:]) or '無')}）有列用每日版，否則 revenue_hist；年增、月增照同一列公告的去年當月、上月營收"
          + (f"；每日版期別錯位列已丟：{ldiag['每日版錯位列（丟掉）']}" if ldiag["每日版錯位列（丟掉）"] else ""),
          "- 欄位：營收＝單月（億元）｜年增、月增＝單月｜3月年增＝近 3 月年增平均｜加速＝近 3 月年增平均 − 近 12 月年增平均（pp）｜"
          "24高 ★＝創 24 個月新高（前 24 月須全有值，不全 ⇒ ?）｜收盤＝未還原｜距高＝還原收盤距近一年最高｜1年＝近一年還原漲幅（含息）｜"
          "高點3降 ▼＝營收年增從近 12 月高點連 3 月下降（警訊，只描述；台股 seq568）",
          ""]
    md = head_lines("月報", key, asof, sha, ac, act, ex)
    hdr = "| 股 | 營收億 | 年增 | 月增 | 3月年增 | 加速 | 24高 | 收盤 | 距高 | 1年 | 高點3降 |"
    sep = "|---|---:|---:|---:|---:|---:|:-:|---:|---:|---:|:-:|"
    for g, gname, subs in GROUPS:
        md += [f"## {g} {gname}", ""]
        gd = df[df["group"] == g]
        isF = g in WARN_GROUPS
        for sub, _ in subs:
            sd = gd[gd["subgroup"] == sub]
            if sub:
                md += [f"**{sub}**", ""]
            md += [hdr + (" 標記 |" if isF else ""), sep + (":-:|" if isF else "")]
            for _, r in sd.iterrows():
                per = "" if r["rev_period"] == P or not r["rev_period"] else f"（{r['rev_period'][2:]}）"
                cells = [f"{r['stock_id']} {r['name']}{per}", fyi(r.get("rev_k")), fpct(r.get("yoy")), fpct(r.get("mom")), fpct(r.get("yoy3")),
                         fpct(r.get("accel"), True), fbool(r.get("hi24")), fpx(r["close"]), fpct(r["pct_from_high"]), fpct(r["ret_1y"]),
                         fbool(r.get("flag_yoy3dn"), "▼")]
                if isF:
                    fl = ("①" if T(r.get("flag_mom2")) else "") + ("②" if T(r.get("flag_drop30")) else "") + ("③" if T(r.get("flag_yoy3dn")) else "")
                    cells.append(fl or "")
                md.append("| " + " | ".join(cells) + " |")
            md.append("")
        if g == "C":
            for sid, th in WATCH.items():
                rr = gd[gd["stock_id"] == sid]
                if len(rr):
                    r = rr.iloc[0]
                    md.append(f"- ⭐ {sid} {r['name']} {r['rev_period']} 單月 {fyi(r.get('rev_k'))} 億：" +
                              ("**≥ 3.9 億**" if T(r.get("flag_watch")) else ("未達 3.9 億" if Fz(r.get("flag_watch")) else "無資料")) + "（只標）")
        if isF:
            f1 = [f"{r['stock_id']}（{fpct(r.get('mom_prev'))}、{fpct(r.get('mom'))}）" for _, r in gd.iterrows() if T(r.get("flag_mom2"))]
            f2 = [f"{r['stock_id']}（{fpct(r['pct_from_high'])}）" for _, r in gd.iterrows() if T(r.get("flag_drop30"))]
            f3 = [r["stock_id"] for _, r in gd.iterrows() if T(r.get("flag_yoy3dn"))]
            md += [f"- ① 營收月增 ≤ 0 連 2 月：{'、'.join(f1) or '無'}", f"- ② 股價距一年高點 ≤ −30%：{'、'.join(f2) or '無'}",
                   f"- ③ 營收年增從高點連 3 月下降：{'、'.join(f3) or '無'}", "- ①②③ 只標、不判。"]
        if g == PAPER_PPI[0]:
            md.append(f"- 造紙報價代理（美國 PPI {PAPER_PPI[2]}，私有庫只出判定）：{paper_ppi_line(asof)}（描述；美國物價代理，不是亞洲紙價）")
        nts = [f"{r['stock_id']}：{r['notes']}" for _, r in gd.iterrows() if r["notes"]]
        cs = [f"{r['stock_id']}：{r['corrections']}" for _, r in gd.iterrows() if r.get("corrections")]
        if nts or cs:
            md += ["", "註："] + [f"- {x}" for x in nts] + [f"- 更正（照實標、值不改）{x}" for x in cs]
        md.append("")
    body = md[len(head_lines("月報", key, asof, sha, ac, act, ex)):]
    LN = line_month(df, P)
    md += g_section(G, asof, P, avail_ok)
    md += ["", "## LINE 摘要", "", *LN, "", "— 回測線（bigrun_monthly 自動產；描述、不判、不計 N）"]
    sec = daily_section(f"月報（{P} 營收）", LN, body)
    return df, md, P, sec


def p0(v):
    return "—" if v is None or not np.isfinite(v) else f"{v * 100:.0f}%"


def line_month(df, P):
    """LINE 摘要（台股 seq539、情報 0030／0035 格式）：≤ 4 行；只寫有變化的；⛔ 不判、不推薦、不寫買賣、不加固定警語。"""
    L = [f"- 【LINE】⭐ 大漲觀察（{int(P[5:])} 月營收）："]
    up, warn = [], []
    for _, r in df.iterrows():
        if r["group"] in WARN_GROUPS:
            if T(r.get("flag_mom2")) or T(r.get("flag_drop30")) or T(r.get("flag_yoy3dn")):
                warn.append(f"{r['group']}：{r['stock_id']} {r['name']}")
            continue
        first_hi = T(r.get("hi24")) and not T(r.get("hi24_prev"))
        if first_hi or (T(r.get("up")) and not T(r.get("up_prev"))):     # 「只寫有變化的」：轉強（字面條件）本期成立、上一期不成立者才列
            up.append(f"{r['group']}：{r['stock_id']} {r['name']} 近 3 月年增 {p0(r.get('yoy3'))}（上月 {p0(r.get('yoy3_prev'))}）"
                      + ("、首次創 24 月新高" if first_hi else ""))
    if up:
        L.append("  轉強：" + "；".join(up))
    if warn:
        L.append("  警訊：" + "；".join(warn))
    if not up and not warn:
        L.append("  本月無變化")
    kp = []
    for sid, th in WATCH.items():
        rr = df[df["stock_id"] == sid]
        if len(rr) and np.isfinite(rr.iloc[0].get("rev_k", np.nan)):
            r = rr.iloc[0]
            kp.append(f"{sid} {r['name']} {int(r['rev_period'][5:])} 月單月 {fyi(r['rev_k'])} 億（{'≥' if T(r.get('flag_watch')) else '未達'} {th / 1e5:g} 億）")
    if kp:
        L.append("  重點：" + "；".join(kp))
    return L


def line_quarter(df, key):
    L = [f"- 【LINE】⭐ 大漲觀察季加報（{key} 財報）："]
    kp = []
    for sid in QWATCH:
        rr = df[df["stock_id"] == sid]
        if len(rr):
            r = rr.iloc[0]
            q = r.get("fs_q")
            kp.append(f"{sid} {r['name']}合約負債年增 {p0(r.get('cl_yoy'))}" + (f"（{q}）" if isinstance(q, str) else "（無可用財報）"))
    L.append("  重點：" + ("、".join(kp) if kp else "本季無變化"))
    return L


def daily_section(title, LN, body):
    """每日名單第十二節：LINE 摘要＋A～F 表（組標題降成 ###，免得切斷節）。"""
    b = [("#" + x) if x.startswith("## ") else x for x in body]
    while b and not b[-1].strip():
        b.pop()
    return [f"{SEC_PREFIX}{title}", "", *LN, "", "- 完整版（含 G 十條 169 檔表、csv）：回測線大漲觀察月報／季加報 md", "", *b]


def put_daily(md_path, sections, prefix=SEC_PREFIX):
    """把每日名單 md 的「## 十二、大漲觀察…」節（prefix 開頭者）整節置換成 sections（[] ＝ 移除）、接檔尾；冪等；其他段逐字不變才寫回。"""
    lines = open(md_path, encoding="utf-8").read().split("\n")

    def strip_ours(ls):
        out, skip = [], False
        for x in ls:
            if x.startswith("## "):
                skip = x.startswith(prefix)
            if not skip:
                out.append(x)
        while out and not out[-1].strip():
            out.pop()
        return out
    base = strip_ours(lines)
    new = list(base)
    for s in sections:
        new += ["", *s]
    if strip_ours(new) != base:
        raise RuntimeError("第十二節置換後其他段有變（不寫回）")
    txt = "\n".join(new) + "\n"
    if txt != "\n".join(lines):
        with open(md_path + ".tmp", "w", encoding="utf-8") as fo:
            fo.write(txt)
        os.replace(md_path + ".tmp", md_path)
    return len(sections)


def g_section(G, asof, P, avail_ok):
    df = G["df"]; M13 = G["M13"]; QK = G["QK"]; pi = G["pinfo"]; pc = G["pcol"]
    lp = M13[-1]; lq = RLP.qlabel(QK[-1])
    n_hi = int((df[f"hi24_{lp}"] == True).sum())   # noqa: E712
    n_top = int((df["pth_top30"] == True).sum())   # noqa: E712
    n_v = int(df["vol20_ge500"].fillna(False).astype(bool).sum())
    md = ["## G 十條供應鏈 169 檔描述表（同 10/20 快照欄位，完整 117 欄見 csv）", "",
          f"- 月營收 {M13[0]}～{lp}（公告當時口徑同上" + ("" if avail_ok else f"；⚠ {lp} 期依可用日規則尚未可用，以已公布值描述") + f"）；季報 {RLP.qlabel(QK[0])}～{lq}；"
          f"PTH 以 {pi['月底']} 全市場重算（排序母體 {pi['排序母體 n']}、前 30% 切點 {pi['切點']}）",
          f"- {lp} 創 24 月新高 {n_hi} 檔｜PTH 前 30% {n_top} 檔｜20 日均量 ≥ 500 張 {n_v} 檔｜缺值 {len(G['missing'])} 列（{G['missing']['stock_id'].nunique()} 檔，見 missing csv）",
          "- 分層、誰先動的解讀由台股策略線做；本表照代號序（不排名）。"]
    if G["lists_missing"]:
        md.append(f"- ⚠ 每日名單檔不在（{G['lists_missing'][0]}）⇒ 營量／營飆三欄空白")
    md += ["", f"| 股 | 年增 | 24高 | 加速 | 存貨天數 | 毛利率 | 距高 | 1年 | PTH前30% |", "|---|---:|:-:|---:|---:|---:|---:|---:|:-:|"]
    for _, r in df.iterrows():
        md.append(f"| {r['stock_id']} {r['name']} | {fpct(r[f'yoy_{lp}'])} | {fbool(r[f'hi24_{lp}'] if pd.notna(r[f'hi24_{lp}']) else np.nan)} | "
                  f"{fpct(r['rev_accel'], True)} | {fnum(r[f'inv_days_{lq}'])} | {fpct(r[f'gm_{lq}'])} | {fpct(r['pct_from_52w_high'])} | {fpct(r['ret_1y'])} | "
                  f"{fbool(r['pth_top30'] if pd.notna(r['pth_top30']) else np.nan, '✔', '')} |")
    md.append(f"\n（存貨天數、毛利率為 {lq}；24高、PTH前30% 空白＝否，? ＝不可判）")
    return md


def quarter_report(asof, sha, ac, act, FD, key, G_nm):
    AF = af_codes(); codes = [c for _, _, _, c in AF]
    FM = fs_metrics(FD, codes, asof, key)
    rows = []
    for g, gname, sub, sid in AF:
        r = {"group": g, "group_name": gname, "subgroup": sub, "stock_id": sid, "name": G_nm.get(sid, "")}
        f = FM[sid]; r.update({k: v for k, v in f.items() if k != "notes"}); r["notes"] = "；".join(f["notes"])
        rows.append(r)
    df = pd.DataFrame(rows)
    ex = [f"- 本季：{key}（法定期限 {fs_deadline(int(key[:4]), int(key[-1])).date()}）；各檔用資料日已可用的最新一季（未到的照實標）",
          "- 財報 fs_xbrl（合併 cr 優先）；可用日＝filing_dates 上傳時戳（同期有 AI1 取 AI1 最早，否則最早文件）≤ 資料日；無時戳不給值（⛔ 不退法定期限）",
          "- 欄位：合約負債＝流動＋非流動（億元；兩欄皆空＝無此科目）｜年增＝對去年同季｜存貨天數＝期末存貨 ÷ 單季營業成本 × 91.25（年初累計差分）｜"
          "毛利率＝單季營業毛利 ÷ 單季營收｜年變化＝本季 − 去年同季（天／pp）", "- 月營收與股價見同月月報。", ""]
    md = head_lines("季加報", key, asof, sha, ac, act, ex)
    hdr = ["| 股 | 季 | 合約負債億 | 年增 | 存貨天數 | 年變化 | 毛利率 | 年變化 |", "|---|:-:|---:|---:|---:|---:|---:|---:|"]
    for g, gname, subs in GROUPS:
        md += [f"## {g} {gname}", ""]
        gd = df[df["group"] == g]
        for sub, _ in subs:
            sd = gd[gd["subgroup"] == sub]
            if sub:
                md += [f"**{sub}**", ""]
            md += hdr
            for _, r in sd.iterrows():
                q = r.get("fs_q", "—")
                md.append(f"| {r['stock_id']} {r['name']} | {q if isinstance(q, str) else '—'} | {fyuan_yi(r.get('cl'))} | {fpct(r.get('cl_yoy'))} | "
                          f"{fnum(r.get('inv_days'))} | {('+' if np.isfinite(r.get('inv_days_chg', np.nan)) and r.get('inv_days_chg') >= 0 else '') + fnum(r.get('inv_days_chg'))} | "
                          f"{fpct(r.get('gm'))} | {fpct(r.get('gm_chg'), True)} |")
            md.append("")
        nts = [f"{r['stock_id']}：{r['notes']}" for _, r in gd.iterrows() if r["notes"]]
        if nts:
            md += ["註："] + [f"- {x}" for x in nts] + [""]
    body = md[len(head_lines("季加報", key, asof, sha, ac, act, ex)):]
    LN = line_quarter(df, key)
    md += ["## LINE 摘要", "", *LN, "", "— 回測線（bigrun_monthly 自動產；描述、不判、不計 N）"]
    return df, md, daily_section(f"季加報（{key}）", LN, body)


# ═════════════ 前瞻紀錄：長線候選確認前先小部位 seq3 ═════════════
SP_TAG = "前瞻紀錄「長線候選確認前先小部位」seq8（446b15cd5b6be0bf；裁定 seq466 核，取代 seq5～7；候選變更依裁定 seq462、seq466 急件）"
SP_CANDS = {"1503": "2026-10-22", "1513": "2026-10-22", "1305": "2026-10-22", "1312": "2026-10-22",   # 代號：起點（核後下一交易日開盤）；增減照台股信改這裡
            "8936": "2026-10-27"}    # seq6／seq462／seq466（10/23 颱風休市、10/26 補假 ⇒ 10/27）；2002、1101、2014 已刪；4510、6609 刪（產業 seq15、使用者 10/24「取消」）；3376 延到 11/13 再判（產業 seq20、使用者 10/25）
SP_CODES = list(SP_CANDS)
_UP27 = "（起點前 2026-09 營收已達轉強定義：近 3 月年增比前 12 月高 5 點以上；回測線 10/24 照登錄定義判）⇒ 檢查時另標、不當「確認前」樣本"
SP_ENTRY_UP = {"1312": "進場時已轉強（起點前 2026-09 營收已轉強；裁定 seq446 §四）⇒ 檢查時另標、不當「確認前」樣本；加碼仍照 2026-11 月報起判"}
SP_ENTRY_UP_DORMANT = {"3376": "進場時已轉強" + _UP27 + "；⚠ 新需求型加碼看燈2、不看轉強（seq8）"}   # 3376 若 11/13 重判過再加回（屆時重判進場時狀態）
SP_SHORTAGE = ["1305", "1312"]                   # 缺貨型（seq8：中鋼、台泥、中鴻已刪）兩個只問不賣提醒
SP_NEWDEMAND = ["3376"]                          # 新需求型（seq8）：加碼改「燈2 亮」（產業判、寄信）⇒ 收信後下一交易日開盤加 2 份；第 12 份月報前燈2 都沒亮 ⇒ 隔天開盤賣
SP_REMIND_TDS = (250, 625)                       # seq6：缺貨型確認後第 250、625 個交易日各問一次（附三項描述）
SP_REMIND_TD = 625
CFG_PPI = "小部位_報價提醒"                      # ① 報價代理連 3 月下跌提醒；缺鍵＝關（資料庫 1023-0134 PPI 到庫 ⇒ 回測線 10/23 開）
SP_PPI = {"1305": ("WPU066", "塑膠"), "1312": ("WPU066", "塑膠")}   # 美國 PPI 代理（缺貨型二輪登錄 §三）；鋼鐵 WPU1017、水泥 WPU1322 隨中鋼、台泥、中鴻刪除停用
US_REPO = os.path.expanduser("~/us-stock-data")  # ⛔ 私有庫：只讀判定、不把序列寫進公開輸出
SP_N_REPORTS, SP_ADD, SP_COST = 12, 2, 0.00585
SP_FIX = "台股 5 檔（10/22 四檔、10/27 一檔；華夏、國喬依使用者 10/25 指示 10/27 開盤賣）、看過新聞才挑、只是前瞻紀錄；10/25 起改依產業大漲主題框架 v4 買賣（裁定 seq473）"
SP_V4 = {"1503", "1513", "8936"}   # 裁定 seq473：這些卡（與之後新買的）改照產業 v4 出場 ①～⑤（產業寄賣信 ⇒ user_sell.csv）；月報轉強只記、⛔ 不自動加碼、⛔ 不放棄
WD = "一二三四五六日"
SP_COLS = ["seq", "stock_id", "name", "event", "trade_date", "price_raw", "units", "status", "report_key", "report_asof",
           "judge", "judge_detail", "note", "recorded_at", "sha"]
BUY_EV = ("起點買進", "轉強加碼")
SELL_EV = "放棄賣出"
USER_SELL_EV = "使用者指示賣出"                 # 產業 seq17／19／20：往前看判準不過 ⇒ 使用者同意賣（⛔ 不算規則本身的放棄）；照 user_sell.csv
SELL_EVS = (SELL_EV, USER_SELL_EV)
SELL_OK = ("未確認賣出", "指示賣出")
SP_FIRST_KEY = "2026-11"                       # 起點後第一份月報（10 月營收）起判；9 月樣本（2026-10 鍵）不算（台股 seq547 ②）
CFG = os.path.join(REPO, "backtest", "forward", "設定_每份金額.json")
CFG_KEY, CFG_AMT = "小部位_LINE", "小部位"     # ⛔ 本模組不改設定檔；「小部位」＝每份金額（只換算 LINE 股數，seq447 不入登錄）
USER_COLS = ["stock_id", "name", "event", "trade_date", "shares", "price", "detail", "source", "note"]
USER_SEED = [   # 情報線 2026-10-22 10:00 信：使用者 10/22 盤中成交（每份 2 萬；非開盤價）
    {"stock_id": "1503", "name": "士電", "event": "起點買進", "trade_date": "2026-10-22", "shares": "104", "price": "194.5", "detail": "104@194.5",
     "source": "情報線 20261022-1000（券商截圖）", "note": "盤中成交、非開盤價"},
    {"stock_id": "1513", "name": "中興電", "event": "起點買進", "trade_date": "2026-10-22", "shares": "123", "price": "163.5", "detail": "123@163.5",
     "source": "情報線 20261022-1000（券商截圖）", "note": "盤中成交、非開盤價"},
    {"stock_id": "1305", "name": "華夏", "event": "起點買進", "trade_date": "2026-10-22", "shares": "1574", "price": "12.7365", "detail": "574@12.8＋1000@12.7",
     "source": "情報線 20261022-1000（券商截圖）", "note": "盤中成交、非開盤價；均價 12.7365"},
    {"stock_id": "1312", "name": "國喬", "event": "起點買進", "trade_date": "2026-10-22", "shares": "1302", "price": "15.25", "detail": "1000＋302@15.25",
     "source": "情報線 20261022-1000（券商截圖）", "note": "盤中成交、非開盤價"},
]


def sp_cfg(path=None):
    try:
        return json.load(open(path or CFG, encoding="utf-8"))
    except Exception:
        return {}


def sp_line_on(path=None):
    return bool(sp_cfg(path).get(CFG_KEY, False))


def months_between(k0, k1):
    return (int(k1[:4]) - int(k0[:4])) * 12 + int(k1[5:]) - int(k0[5:])


def sp_shares(units, close, cfg):
    """LINE 股數 ＝ 設定「小部位」× 份數 ÷ 未還原收盤（零股取整）；缺鍵或收盤缺 ⇒ None。"""
    amt = cfg.get(CFG_AMT)
    if not amt or close is None or not np.isfinite(close) or close <= 0:
        return None
    return int(float(amt) * units // close)


def _sh(n):
    return f"（約 {n:,} 股）" if n is not None else "（股數照你決定）"


def sp_events_report(new_rows, closes, cfg):
    """本份月報的小部位事件行（⛔ 不計入 LINE 摘要 4 行［seq444］；⛔ 不寫報酬）。closes ＝ {代號: 月報資料日未還原收盤}。"""
    out = []
    for r in new_rows:
        if r["event"] != "月報判定":
            continue
        if r["judge"] == "轉強":
            out.append(f"  小部位：{r['stock_id']} {r['name']} 轉強 ⇒ 明天開盤加 {SP_ADD} 份{_sh(sp_shares(SP_ADD, closes.get(r['stock_id']), cfg))}")
        elif "放棄判定" in r["note"]:
            why = "燈2 仍未亮" if r["stock_id"] in SP_NEWDEMAND else "仍未轉強"
            out.append(f"  小部位：{r['stock_id']} {r['name']} 第 {SP_N_REPORTS} 份月報{why} ⇒ 明天開盤賣")
    return out


def _hol_sets(H):
    hol, trade = set(), set()
    p = os.path.join(H, "meta", "holiday_schedule.csv")
    if os.path.exists(p):
        h = pd.read_csv(p, dtype=str)
        h = h[h["date"].astype(str).str.match(r"^\d{4}-\d{2}-\d{2}$", na=False)]
        for d, n, t in zip(h["date"], h["name"].fillna(""), h["note"].fillna("")):
            (trade if (any(k in n for k in ("開始交易", "最後交易")) and "無交易" not in t) else hol).add(d)
    return hol, trade


def _is_td(d, hol, trade):
    s = d.strftime("%Y-%m-%d")
    return s not in hol and (d.weekday() < 5 or s in trade)


def next_trading_day(H, asof):
    """下一交易日（外推）：週一～五且不在休市表；休市表讀法同 run_daily_list（名稱含開始／最後交易且附註沒寫無交易 ⇒ 交易日）。"""
    hol, trade = _hol_sets(H)
    d = asof + pd.Timedelta(days=1)
    while not _is_td(d, hol, trade):
        d += pd.Timedelta(days=1)
    return d


def prev_trading_day(H, d):
    """d 之前（不含）最近一個交易日（外推，同上讀法）。"""
    hol, trade = _hol_sets(H)
    d = d - pd.Timedelta(days=1)
    while not _is_td(d, hol, trade):
        d -= pd.Timedelta(days=1)
    return d


NOW_OVERRIDE = None                               # 測試用：固定「台北現在」


def taipei_now():
    return NOW_OVERRIDE if NOW_OVERRIDE is not None else pd.Timestamp.now(tz=TZ).tz_localize(None)


def sp_notify(rows, cal, asof, H, closes, cfg, names, now, sha, ppi=None, lamp2=None, desc=None, usell=None):
    """小部位通知列（寫進 smallpos.csv：只記一次、已寫凍結；LINE 行原文存在 judge_detail，同資料日名單重產時原樣補回）：
    ・新候選（seq447 §二、seq458 §二、seq461「10/26 晚推」）：起點前一個日曆日（＝前一晚；10/23 颱風休市不在休市表，改用日曆日）台北 14:00 後、或之後到起點前的第一次執行 ⇒
      「  小部位：代號 名稱 新候選 ⇒ 10/27（二）開盤買 1 份（約 N 股）」；以「台北今天」判，不看資料日（資料日落後也照出、起點後不再出）。
    ・缺貨型確認後滿 250、625 個交易日（seq6）：確認那份月報資料日之後第 N 個交易日起第一次執行 ⇒「  小部位：代號 名稱 確認後已滿 N 個交易日 ⇒ 續抱或賣？（你決定）｜三項描述」
      （desc(sid, 確認列, 資料日) 回三項描述字串；None ⇒ 不附）。
    ・新需求型燈2（seq8）：lamp2 有列、尚未加碼 ⇒「  小部位：代號 名稱 燈2 亮 ⇒ M/D（週）開盤加 2 份（約 N 股）」（只出一次）。
    回『要新增』的列。"""
    new = []
    allr = lambda: rows + new                                              # noqa: E731

    def add(sid, ev, line, note):
        r = {c: "" for c in SP_COLS}
        r.update(seq=str(len(rows) + len(new) + 1), stock_id=sid, name=names.get(sid, ""), event=ev, report_asof=str(asof.date()),
                 judge_detail=line, note=note, recorded_at=str(now)[:19], sha=sha[:10])
        new.append(r)
    today = now.normalize()
    sold = lambda sid: any(r["stock_id"] == sid and r["event"] in SELL_EVS for r in allr())   # noqa: E731
    for sid, (sd, why, src) in (usell or {}).items():                   # 使用者指示賣出：預定日前一晚（日曆日）14:00 後第一次執行，只一次
        if sid not in SP_CODES or sold(sid) or not today < sd or any(r["stock_id"] == sid and r["event"] == "提醒" and "指示賣出" in r["note"] for r in allr()):
            continue
        fire = sd - pd.Timedelta(days=1)
        if (today == fire and now.hour >= 14) or fire < today:
            add(sid, "提醒", f"  小部位：{sid} {names.get(sid, '')} ⇒ {sd.month}/{sd.day}（{WD[sd.weekday()]}）開盤賣（{why}）",
                f"指示賣出 {sd.date()} 開盤（{src}）")
    for sid, st in SP_CANDS.items():
        st = pd.Timestamp(st)
        if any(r["stock_id"] == sid and r["event"] in ("起點買進", "新候選通知") for r in allr()) or not today < st:
            continue
        fire = st - pd.Timedelta(days=1)
        if (today == fire and now.hour >= 14) or fire < today:
            n = sp_shares(1, closes.get(sid), cfg)
            add(sid, "新候選通知", f"  小部位：{sid} {names.get(sid, '')} 新候選 ⇒ {st.month}/{st.day}（{WD[st.weekday()]}）開盤買 1 份{_sh(n)}",
                f"起點 {st.date()} 開盤；台北 {now:%Y-%m-%d %H:%M} 推（資料日 {asof.date()}）")
    for sid in SP_SHORTAGE:
        cf = next((r for r in allr() if r["stock_id"] == sid and r["event"] == "月報判定" and r["judge"] == "轉強"), None)
        if cf is None or sold(sid):
            continue
        n_td = int(((cal > pd.Timestamp(cf["report_asof"])) & (cal <= asof)).sum())
        for nn in SP_REMIND_TDS:                                           # 只出最大的已到者（兩個一起到 ⇒ 只出 625）；各只一次
            tag = f"確認後滿 {nn} 交易日"
            if n_td < nn or any(r["stock_id"] == sid and r["event"] == "提醒" and tag in r["note"] for r in allr()):
                continue
            if any(n_td >= m for m in SP_REMIND_TDS if m > nn):
                continue
            dsc = desc(sid, cf, asof) if desc is not None else ""
            add(sid, "提醒", f"  小部位：{sid} {names.get(sid, '')} 確認後已滿 {nn} 個交易日 ⇒ 續抱或賣？（你決定）" + (f"｜{dsc}" if dsc else ""),
                f"{tag}（確認＝{cf['report_key']} 月報 {cf['report_asof']}；已過 {n_td} 日）；只問不賣（seq6）")
    for sid, (d, mail, url) in (lamp2 or {}).items():                         # seq8 燈2 通知（只一次；已加碼或已放棄不出）
        if sid not in SP_CODES or any(r["stock_id"] == sid and (r["event"] == "轉強加碼" or (r["event"] == "提醒" and "燈2" in r["note"])
                                                                 or "放棄判定" in r["note"]) for r in allr()):
            continue
        st = pd.Timestamp(SP_CANDS[sid])
        nd = next_trading_day(H, max(d, st - pd.Timedelta(days=1)))
        n = sp_shares(SP_ADD, closes.get(sid), cfg)
        add(sid, "提醒", f"  小部位：{sid} {names.get(sid, '')} 燈2 亮 ⇒ {nd.month}/{nd.day}（{WD[nd.weekday()]}）開盤加 {SP_ADD} 份{_sh(n)}",
            f"燈2 {d.date()} 亮（{mail}；{url}）；收信後下一交易日開盤加碼（seq8）")
    for sid, line, st0, last, k in sp_ppi_hits(asof, names, cfg, ppi):        # seq5 ①：同一段下跌（段起月相同）只推一次
        if sold(sid):
            continue
        tag = f"報價代理 {SP_PPI[sid][0]}（{SP_PPI[sid][1]}）段起 {st0}"
        if any(r["stock_id"] == sid and r["event"] == "提醒" and tag in r["note"] for r in allr()):
            continue
        add(sid, "提醒", line, f"{tag}；最新已發布 {last}、連 {k} 個月月增＜0（美國 PPI 代理）；只問不賣（seq5 ①）")
    return new


def ppi_loader(asof, repo=US_REPO, fetch=True, codes=None, raw=False):
    """私有庫 us-stock-data origin/main 的 FRED PPI（資料庫 1023-0134）⇒ loader(sid)：該業代理月序列（index＝'YYYY-MM'、值＝現行值），
    只留發布日（ppi_first_release first_release_date，缺則 ppi_release_date）＜ 資料日的月份。讀不到 ⇒ 回 None（提醒不出、印一行）。"""
    import io as _io
    try:
        if fetch:
            subprocess.run(["git", "-C", repo, "fetch", "-q", "origin"], timeout=90, capture_output=True)
        show = lambda f: subprocess.run(["git", "-C", repo, "show", f"origin/main:data/macro/{f}"], capture_output=True, check=True,  # noqa: E731
                                        timeout=60).stdout.decode("utf-8")
        rel = pd.read_csv(_io.StringIO(show("ppi_first_release.csv")), dtype=str)
        rel["d"] = pd.to_datetime(rel["first_release_date"].fillna(rel["ppi_release_date"]), errors="coerce")
        ser = {}
        for code in sorted(codes or {c for c, _ in SP_PPI.values()}):
            df = pd.read_csv(_io.StringIO(show(f"fred_{code}.csv")))
            dc, vc = df.columns[0], [c for c in df.columns[1:]][0]
            v = pd.Series(pd.to_numeric(df[vc], errors="coerce").values, index=pd.to_datetime(df[dc]).dt.strftime("%Y-%m"))
            ok = set(rel.loc[(rel["series"] == code) & (rel["d"] < asof), "period"])
            ser[code] = v[[m in ok for m in v.index]].sort_index()
            r = rel[rel["series"] == code].set_index("period")["d"]
            ser[code].attrs["rel"] = {m: r.get(m) for m in ser[code].index}
    except Exception as e:                                                     # noqa: BLE001
        print(f"小部位報價提醒：讀私有庫 PPI 失敗（{type(e).__name__}）⇒ 本晚不出")
        return None
    if raw:
        return lambda code: ser.get(code)
    return lambda sid: ser.get(SP_PPI[sid][0]) if sid in SP_PPI else None


def paper_ppi_line(asof, loader=None):
    """先盯組造紙「報價年增轉正」：最新已發布月年增 ≥ 0 且上一個已發布月 < 0 ⇒ 轉正；否則寫仍正／仍負（⛔ 不出值）。"""
    try:
        s = (loader or ppi_loader(asof, codes=(PAPER_PPI[2],), raw=True))(PAPER_PPI[2])
    except Exception:                                                      # noqa: BLE001
        s = None
    if s is None or len(s.dropna()) < 14:
        return "讀不到（本月不寫）"
    s = s.dropna()
    y = s / s.shift(12) - 1
    if not (np.isfinite(y.iloc[-1]) and np.isfinite(y.iloc[-2])):
        return "資料不足"
    st = "**轉正**" if (y.iloc[-1] >= 0 > y.iloc[-2]) else ("仍正" if y.iloc[-1] >= 0 else "仍負")
    return f"年增{st}（最新已發布 {s.index[-1]}）"


def sp_ppi_hits(asof, names, cfg, loader):
    """seq5 ①：缺貨型四檔該業報價代理「最新已發布月」為連續月增 < 0 的第 3 個月以上 ⇒ (代號, LINE 行, 段起月, 最新月, 連跌月數)；同一段下跌只推一次由呼叫端以段起月去重。
    ⭐ 最新月須在起點（進場）當天或之後才發布（有發布日時；登錄 §三「只看進場後」）：進場前就已知的連跌不推，要等進場後發布的那個月仍跌才推。"""
    if not bool(cfg.get(CFG_PPI, False)) or loader is None:
        return []
    out = []
    for sid in SP_SHORTAGE:
        s = loader(sid)
        if s is None or len(s.dropna()) < 4:
            continue
        m = s.dropna().pct_change().dropna()
        k = 0
        while k < len(m) and m.iloc[-1 - k] < 0:
            k += 1
        d_last = s.attrs.get("rel", {}).get(m.index[-1])
        if k >= 3 and not (d_last is not None and sid in SP_CANDS and d_last < pd.Timestamp(SP_CANDS[sid])):
            out.append((sid, f"  小部位：{sid} {names.get(sid, '')} 報價代理連 {k} 個月下跌 ⇒ 續抱或賣？（你決定）", m.index[-k], m.index[-1], k))
    return out


def sp_ppi_lines(rows, asof, names, cfg, loader=None):
    """seq5 ①：缺貨型四檔報價代理連 3 個月月增 < 0 ⇒「  小部位：代號 名稱 報價代理連 3 個月下跌 ⇒ 續抱或賣？（你決定）」。
    設定「小部位_報價提醒」缺鍵／false ⇒ 不出；loader 為 None（私有庫讀不到）⇒ 不出並印一行。檢查與紀錄列用 sp_ppi_hits（本函式只回行）。
    loader(sid) ⇒ 該業報價代理月序列（pd.Series，index＝月、值＝指數；只用發布日 ≤ 資料日的月份）。"""
    if not bool(cfg.get(CFG_PPI, False)):
        return []
    if loader is None:
        print("小部位報價提醒：已開但報價代理資料讀不到 ⇒ 本晚不出")
        return []
    return [h[1] for h in sp_ppi_hits(asof, names, cfg, loader)]


def sp_event_lines(rows, asof):
    """本資料日要推的小部位通知行（新候選、625 日提醒）：通知列 report_asof ＝ 資料日者原樣補回（名單同資料日重產也只是同一則）。"""
    return [r["judge_detail"] for r in rows if r["event"] in ("新候選通知", "提醒") and r["report_asof"] == str(asof.date()) and r["judge_detail"]]


def sp_night_lines(rows, asof, names):
    """今晚要推的小部位通知行（設定「小部位_LINE」開才有）：新候選／625 日提醒（紀錄列）＋報價提醒（另一開關「小部位_報價提醒」，10/23 開；寫成紀錄列）。"""
    if not sp_line_on():
        return []
    return sp_event_lines(rows, asof)              # 報價提醒 10/23 起改寫成紀錄列（sp_notify），隨 sp_event_lines 補回


def sp_event_secs(ev):
    """非月報夜的小部位通知行 ⇒ 每日名單另一節（月報夜則插進月報 LINE 摘要）。"""
    return [[f"{SEC_PREFIX}小部位（通知）", "", "- 【LINE】⭐ 大漲觀察（小部位）：", *ev]] if ev else []


def insert_line_events(lines, ev):
    """把事件行插在第一則【LINE】大漲觀察 區塊的續行之後（不計入摘要 4 行）。"""
    if not ev:
        return lines
    i = next((j for j, x in enumerate(lines) if x.startswith("- 【LINE】⭐ 大漲觀察")), None)
    if i is None:
        return lines
    j = i + 1
    while j < len(lines) and lines[j].startswith("  ") and not lines[j].startswith("  - "):
        j += 1
    return lines[:j] + ev + lines[j:]


def sp_load(p):
    if os.path.exists(p):
        return pd.read_csv(p, dtype=str, keep_default_na=False, encoding="utf-8-sig").to_dict("records")
    return []


class RawPx:
    """未還原日線（開、高、低、收）＋前一有成交日收盤；給買賣成交價與鎖漲跌停判斷。"""
    def __init__(self, H):
        self.H = H; self.c = {}

    def bar(self, sid, d):
        if sid not in self.c:
            x = pd.read_csv(os.path.join(self.H, "stocks", f"{sid}.csv"), usecols=["date", "open", "high", "low", "close"])
            x["date"] = pd.to_datetime(x["date"]); x = x.drop_duplicates("date").set_index("date").sort_index()
            x = x.apply(pd.to_numeric, errors="coerce"); x = x[(x["close"] > 0) & (x["open"] > 0)]
            self.c[sid] = x
        x = self.c[sid]
        if d not in x.index:
            return None
        k = x.index.get_loc(d)
        r = x.iloc[k]
        return {"o": float(r["open"]), "h": float(r["high"]), "l": float(r["low"]), "c": float(r["close"]),
                "pc": float(x["close"].iloc[k - 1]) if k > 0 else np.nan}


def _locked(b, up):
    """開盤鎖漲停（開＝漲停價 ∧ 低＝開）／開盤鎖跌停（開＝跌停價 ∧ 高＝開）；參考價用前一有成交日未還原收盤（除權息日參考價不同 ⇒ 可能漏判，照實）。"""
    if b is None or not np.isfinite(b["pc"]):
        return False
    from backtest.research11 import limit_price
    lp = limit_price(b["pc"], up, 0.10)
    return abs(b["o"] - lp) < 1e-6 and abs((b["l"] if up else b["h"]) - b["o"]) < 1e-6


def sp_update(rows, cal, asof, px, judgments, names, now, sha, lamp2=None, usell=None):
    """回『要新增』的列（⛔ 不改舊列＝已寫凍結）。judgments ＝ [(月報鍵, 月報資料日, {代號: {up, up_prev, judged, det, det_prev}})]。
    第 i 份月報 ＝ 該檔第一份判定月報起算的月數 ＋ 1；第 12 份仍未轉強 ⇒ 放棄判定；當期營收未公布 ⇒ 記「未判」、下一份補判上一期
    （第 12 份未判 ⇒ 第 13 份只補判上一期、以它為放棄判定）。"""
    new = []
    allr = lambda: rows + new                                              # noqa: E731

    def has(sid, ev, **kw):
        return any(r["stock_id"] == sid and r["event"] == ev and all(str(r.get(k)) == str(v) for k, v in kw.items()) for r in allr())

    def add(sid, ev, **kw):
        r = {c: "" for c in SP_COLS}
        r.update(seq=str(len(rows) + len(new) + 1), stock_id=sid, name=names.get(sid, ""), event=ev, recorded_at=now, sha=sha[:10])
        r.update({k: ("" if v is None else str(v)) for k, v in kw.items()})
        new.append(r)

    def buy(sid, ev, d, units, **kw):
        b = px.bar(sid, d)
        if b is None:
            add(sid, ev, trade_date=d.date(), units=0, status="買不到（當日無成交）", **kw)
        elif _locked(b, True):
            add(sid, ev, trade_date=d.date(), price_raw=b["o"], units=0, status="買不到（開盤鎖漲停）", **kw)
        else:
            add(sid, ev, trade_date=d.date(), price_raw=b["o"], units=units, status="成交", **kw)

    def jrows(sid):
        return [r for r in allr() if r["stock_id"] == sid and r["event"] == "月報判定"]
    cal = cal[cal <= asof]
    lamp2 = lamp2 if lamp2 is not None else {}
    usell = usell if usell is not None else {}
    sold = lambda sid: any(r["stock_id"] == sid and r["event"] in SELL_EVS for r in rows + new)   # noqa: E731
    # ① 起點：核後下一交易日（或之後第一個交易日）開盤 1 份；國喬另標「進場時已轉強」
    for sid, st in SP_CANDS.items():
        d0 = cal[cal >= pd.Timestamp(st)]
        if len(d0) and not has(sid, "起點買進"):
            buy(sid, "起點買進", d0[0], 1, note=f"補記：起點＝核後下一交易日 {st} 開盤（未還原開盤）；由月報模組於資料日 {asof.date()} 晚補記")
        if len(d0) and sid in SP_ENTRY_UP and not has(sid, "標記"):
            add(sid, "標記", note=SP_ENTRY_UP[sid])
    # ② 月報判定（每期照判狀態，⛔ 不套 LINE「上期沒轉強才列」）
    for key, ra, J in judgments:
        if key < SP_FIRST_KEY:
            continue
        for sid in SP_CODES:
            if sid not in J or ra < pd.Timestamp(SP_CANDS[sid]) or sold(sid):
                continue
            js = jrows(sid)
            if sid in SP_V4:                                               # 裁定 seq473：v4 卡只記營收狀態
                if any(r["report_key"] == key for r in js):
                    continue
                i = months_between(min([r["report_key"] for r in js] + [key]), key) + 1
                add(sid, "月報判定", report_key=key, report_asof=ra.date(), judge="只記（v4）",
                    judge_detail=("轉強｜" if J[sid]["up"] else "未轉強｜") + J[sid]["det"],
                    note=f"第 {i} 份月報；10/25 起照產業大漲主題框架 v4（裁定 seq473）：轉強只記、不自動加碼、不放棄；加碼與賣出照產業信")
                continue
            if sid in SP_NEWDEMAND:                                        # seq8：燈2 判、營收只記；不受營收未公布影響
                if any(r["judge"] == "燈2已亮" or "放棄判定" in r["note"] for r in js) or any(r["report_key"] == key for r in js):
                    continue
                first = min([r["report_key"] for r in js] + [key])
                i = months_between(first, key) + 1
                lit = sid in lamp2 and lamp2[sid][0] <= ra
                note = f"第 {i} 份月報；新需求型看燈2（seq8）、營收只記"
                if lit:
                    note += f"；燈2 {lamp2[sid][0].date()} 亮（{lamp2[sid][1]}）"
                elif i >= SP_N_REPORTS:
                    note += f"；放棄判定（第 {SP_N_REPORTS} 份月報前燈2 都沒亮 ⇒ 該份月報隔天開盤賣、記未確認）"
                add(sid, "月報判定", report_key=key, report_asof=ra.date(), judge="燈2已亮" if lit else "燈2未亮",
                    judge_detail="營收（只記）：" + J[sid]["det"], note=note)
                continue
            if any(r["judge"] == "轉強" or "放棄判定" in r["note"] for r in js) or any(r["report_key"] == key for r in js):
                continue                                                   # 已確認／已放棄／本份已判
            first = min([r["report_key"] for r in js] + [key])
            i = months_between(first, key) + 1
            pending = bool(js) and js[-1]["judge"].startswith("未判")
            j = J[sid]
            if i > SP_N_REPORTS and not pending:
                continue
            if not j["judged"]:
                add(sid, "月報判定", report_key=key, report_asof=ra.date(), judge="未判（當期營收未公布）",
                    note=f"第 {i} 份月報；當期營收未公布 ⇒ 不判（不算未轉強）、下一份補判")
                continue
            if i > SP_N_REPORTS:                                           # 第 12 份當期未公布 ⇒ 這份只補判上一期，並作為放棄判定
                up, det = j["up_prev"], "補判上一期：" + j["det_prev"]
            else:
                up = j["up"] or (pending and j["up_prev"])
                det = j["det"] + (f"；補判上一期：{'轉強' if j['up_prev'] else '未轉強'}（{j['det_prev']}）" if pending else "")
            note = f"第 {i} 份月報"
            if not up and i >= SP_N_REPORTS:
                note += f"；放棄判定（第 {SP_N_REPORTS} 份月報仍未轉強 ⇒ 該份月報隔天開盤賣、記未確認）"
            add(sid, "月報判定", report_key=key, report_asof=ra.date(), judge="轉強" if up else "未轉強", judge_detail=det, note=note)
    # ③ 轉強 ⇒ 月報隔一交易日開盤加 2 份（每檔一次；買不到也算這一次）｜新需求型：燈2 收信後下一交易日開盤加 2 份（已放棄者不加）
    for sid in SP_NEWDEMAND:
        if sid not in lamp2 or has(sid, "轉強加碼") or not has(sid, "起點買進") or any("放棄判定" in r["note"] for r in jrows(sid)):
            continue
        d, mail, url = lamp2[sid]
        nd = cal[cal > max(d, pd.Timestamp(SP_CANDS[sid]))]
        if len(nd):
            buy(sid, "轉強加碼", nd[0], SP_ADD, report_asof=d.date(), note=f"燈2 亮（{mail}；{url}）⇒ 收信後下一交易日開盤加碼（seq8；每檔只加一次）")
    for sid in SP_CODES:
        if sid in SP_NEWDEMAND:
            continue
        cf = next((r for r in jrows(sid) if r["judge"] == "轉強"), None)
        if cf and not has(sid, "轉強加碼"):
            nd = cal[cal > pd.Timestamp(cf["report_asof"])]
            if len(nd):
                buy(sid, "轉強加碼", nd[0], SP_ADD, report_key=cf["report_key"], report_asof=cf["report_asof"],
                    note="月報判定轉強 ⇒ 月報隔天開盤加碼（每檔只加一次）")
    # ④' 使用者指示賣出（產業 seq17／19／20）：預定日（或之後第一個可賣開盤）開盤賣全部持股；無成交／開盤鎖跌停順延
    for sid, (sd, why, src) in usell.items():
        if sid not in SP_CODES or sold(sid):
            continue
        held = sum(int(r["units"] or 0) for r in allr() if r["stock_id"] == sid and r["event"] in BUY_EV and r["status"] == "成交")
        skipped = []
        for d in cal[cal >= sd]:
            b = px.bar(sid, d)
            if b is None or _locked(b, False):
                skipped.append(f"{d.date()}{'無成交' if b is None else '開盤鎖跌停'}"); continue
            add(sid, USER_SELL_EV, trade_date=d.date(), price_raw=b["o"], units=-held, status="指示賣出" if held else "指示賣出（無持股）",
                note=f"{why}（{src}）⛔ 不算規則本身的放棄" + (f"（順延：{'、'.join(skipped)}）" if skipped else ""))
            break
    # ④ 放棄 ⇒ 放棄判定那份月報隔天開盤賣出（未確認）；無成交／開盤鎖跌停 ⇒ 順延到下一個可賣的交易日
    for sid in SP_CODES:
        ab = next((r for r in jrows(sid) if "放棄判定" in r["note"]), None)
        if ab is None or sold(sid):
            continue
        held = sum(int(r["units"] or 0) for r in allr() if r["stock_id"] == sid and r["event"] in BUY_EV and r["status"] == "成交")
        days = cal[cal > pd.Timestamp(ab["report_asof"])]
        if not held:
            if len(days):
                add(sid, SELL_EV, trade_date=days[0].date(), units=0, status="未確認（無持股）", report_key=ab["report_key"], report_asof=ab["report_asof"])
            continue
        skipped = []
        for d in days:
            b = px.bar(sid, d)
            if b is None or _locked(b, False):
                skipped.append(f"{d.date()}{'無成交' if b is None else '開盤鎖跌停'}"); continue
            add(sid, SELL_EV, trade_date=d.date(), price_raw=b["o"], units=-held, status="未確認賣出", report_key=ab["report_key"],
                report_asof=ab["report_asof"], note=f"第 {SP_N_REPORTS} 份月報仍未轉強 ⇒ 隔天開盤賣出" + (f"（順延：{'、'.join(skipped)}）" if skipped else ""))
            break
    return new


def sp_value(rows, asof, adj_df):
    """照規則（還原價、含息；每份扣 0.585%）：買進＝開盤價；未賣 ⇒ 資料日（或之前最後有成交日）還原收盤；已賣 ⇒ 賣出日還原開盤。
    回 {代號: (份數, 累計報酬)}、合計 (份數, 累計報酬)、最大回落（市值÷投入，未扣成本）。"""
    out = {}; tot_u = 0; tot_r = 0.0; curves = []
    for sid in SP_CODES:
        lots = [r for r in rows if r["stock_id"] == sid and r["event"] in BUY_EV and r["status"] == "成交" and pd.Timestamp(r["trade_date"]) <= asof]
        sell = [r for r in rows if r["stock_id"] == sid and r["event"] in SELL_EVS and r["status"] in SELL_OK and pd.Timestamp(r["trade_date"]) <= asof]
        u = sum(int(r["units"]) for r in lots)
        if not u:
            out[sid] = (0, np.nan); continue
        df = adj_df(sid)
        c = df["close"][df.index <= asof].ffill()
        sd = pd.Timestamp(sell[0]["trade_date"]) if sell else None
        ex = float(df.at[sd, "open"]) if sd is not None else float(c.dropna().iloc[-1])
        rs = sum(int(r["units"]) * (ex / float(df.at[pd.Timestamp(r["trade_date"]), "open"]) - 1 - SP_COST) for r in lots)
        out[sid] = (u, rs / u); tot_u += u; tot_r += rs
        for r in lots:
            d = pd.Timestamp(r["trade_date"]); e = float(df.at[d, "open"]); w = int(r["units"])
            v = (c[c.index >= d] / e * w)
            if sd is not None:
                v = v[v.index < sd].reindex(c.index[c.index >= d]).fillna(ex / e * w)
            curves.append((v, pd.Series(float(w), index=v.index)))
    mdd = np.nan
    if curves:
        V = sum(v.reindex(sorted(set().union(*[x.index for x, _ in curves]))).fillna(0) for v, _ in curves)
        I = sum(i.reindex(V.index).fillna(0) for _, i in curves)
        ratio = (V / I).dropna()
        mdd = float((ratio / ratio.cummax() - 1).min()) if len(ratio) else np.nan
    return out, (tot_u, tot_r / tot_u if tot_u else np.nan), mdd


def user_load(p):
    return sp_load(p)


def user_add(p, row):
    """使用者實際欄補記（情報回報成交後由回測線叫用；只追加）：row 需 USER_COLS 各鍵（event：起點買進／轉強加碼／放棄賣出；shares 賣出為負）。"""
    miss = [c for c in USER_COLS if c not in row]
    if miss:
        raise ValueError(f"使用者實際欄缺欄 {miss}")
    hdr = not os.path.exists(p)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    pd.DataFrame([row], columns=USER_COLS).to_csv(p, mode="a", header=hdr, index=False, encoding="utf-8-sig" if hdr else "utf-8")


def user_value(urows, asof, adj_df, px):
    """使用者實際：成交價換算到還原價（× 當日還原收盤 ÷ 未還原收盤）、依成交金額加權、同樣扣 0.585%；只計成交日 ≤ 資料日。"""
    out = {}
    for sid in SP_CODES:
        U = [r for r in urows if r["stock_id"] == sid and pd.Timestamp(r["trade_date"]) <= asof]
        buys = [r for r in U if int(float(r["shares"])) > 0]
        sells = [r for r in U if int(float(r["shares"])) < 0]
        sh = sum(int(float(r["shares"])) for r in buys)
        if not sh:
            out[sid] = (0, np.nan, np.nan); continue
        df = adj_df(sid)

        def fac(d):
            b = px.bar(sid, d)
            return float(df.at[d, "close"]) / b["c"] if b else np.nan
        cost = sum(int(float(r["shares"])) * float(r["price"]) for r in buys)
        avg = cost / sh
        if sells:
            s = sells[0]; ex = float(s["price"]) * fac(pd.Timestamp(s["trade_date"]))
        else:
            ex = float(df["close"][df.index <= asof].dropna().iloc[-1])
        r_ = sum(int(float(r["shares"])) * float(r["price"]) * (ex / (float(r["price"]) * fac(pd.Timestamp(r["trade_date"]))) - 1 - SP_COST) for r in buys) / cost
        out[sid] = (sh - sum(-int(float(r["shares"])) for r in sells), avg, r_)
    return out


def sp_section(rows, urows, asof, adj_df, px, names, dry, df=None, bench=None):
    val, (tu, tr), mdd = sp_value(rows, asof, adj_df)
    uv = user_value(urows, asof, adj_df, px)
    md = ["## 確認前小部位前瞻（前瞻紀錄；不計 N、金額不記；LINE 只推事件行）", "", f"- {SP_FIX}",
          f"- {SP_TAG}｜照規則（等額份數）：核後下一交易日開盤各 1 份；月報判定轉強（近 3 月營收年增 ≥ 前 12 月 ＋5 點，或首次創 24 月新高；每期照判；轉強條件已驗（暫定）：營收轉強驗證 seq2 合格（暫定），中位約 0、確認段輸大盤報酬指數）"
          f"⇒ 月報隔天開盤加 2 份（只加一次）；起點後第 1 份（{SP_FIRST_KEY}）到第 {SP_N_REPORTS} 份月報都沒判轉強 ⇒ 第 {SP_N_REPORTS} 份月報隔天開盤賣出、記「未確認」；"
          f"月報當期營收未公布 ⇒ 該期不判、下一份補判（第 {SP_N_REPORTS} 份未公布 ⇒ 以補判那份為放棄判定、賣出順延到該份隔天開盤）。"
          "已確認：1503、1513、8936 不設停損、不設天數，持有到使用者另定；缺貨型（1305、1312）照抱、不設停損、不設天數，"
          "另兩個只問不賣的 LINE 提醒：①該業報價代理連 3 個月月增 < 0（美國 PPI 代理：塑膠 WPU066；最新月須在進場後發布，同一段下跌只推一次）"
          "②確認後第 250、625 個交易日各問一次（附：同業擴產／復產、營收年增是否從確認後高點連 3 月下降、股價距確認後最高收盤）。"
          "新需求型 3376：加碼改看燈2（台廠法說第一次上修或量產時程正式定案，產業判、寄信附網址與日期）⇒ 收信後下一交易日開盤加 2 份；第 12 份月報前燈2 都沒亮 ⇒ 隔天開盤賣（seq8；燈2 是新聞判斷、不是回測，依據的 16 段全是贏家）。"
          "同一共同方向台美合計最多 3 檔。1312 進場時已轉強，檢查時不當「確認前」樣本。"
          "⚠ 10/25 使用者指示（產業 seq15／17／19／20）：4510、6609 取消；3376 延到 11/13 再判；1305、1312 往前看判準不過 ⇒ 10/27 開盤賣（記「使用者指示賣出」，⛔ 不算規則本身的放棄）；"
          "出場另加「每月重判往前看判準、不過就賣」待台股 seq9／裁定核。",
          "- 報酬：照規則＝還原價（含息）、每份扣成本 0.585%；使用者實際＝成交價（換算還原）、依成交金額加權、同樣扣 0.585%。smallpos.csv／smallpos_user.csv 只追加、已寫凍結。",
          ""]
    if dry:
        md += ["- （乾跑：本節以既有紀錄＋本次試算顯示，⛔ 未寫入 smallpos.csv）", ""]
    md += ["| 股 | 狀態 | 已判 | 照規則份數 | 照規則累計 | 實際股數 | 實際均價 | 實際累計 |", "|---|---|:-:|---:|---:|---:|---:|---:|"]
    for sid in SP_CODES:
        R = [r for r in rows if r["stock_id"] == sid]
        st = next((r for r in R if r["event"] == "起點買進"), None)
        ad = next((r for r in R if r["event"] == "轉強加碼"), None)
        js = [r for r in R if r["event"] == "月報判定"]
        cf = next((r for r in js if r["judge"] in ("轉強", "燈2已亮")), None)
        if cf is None and sid in SP_NEWDEMAND and ad is not None:
            cf = {"report_key": f"燈2 {ad['report_asof']}"}
        ab = next((r for r in js if "放棄判定" in r["note"]), None)
        sl = next((r for r in R if r["event"] in SELL_EVS), None)
        nj = sum(1 for r in js if r["judge"] in ("轉強", "未轉強", "燈2已亮", "燈2未亮", "只記（v4）"))
        if st is None:
            state = f"起點 {SP_CANDS[sid]} 開盤（尚未到）"
        elif sl is not None:
            state = {"未確認賣出": "未確認・已賣出", "指示賣出": "使用者指示賣出（往前看判準不過）"}.get(sl["status"], sl["status"])
        elif ab is not None:
            state = "未確認・明天開盤賣"
        elif cf is not None:
            state = (f"已確認（{cf['report_key']}" + ("" if cf["report_key"].startswith("燈2") else " 月報") + "）") + ("" if ad else "・明天開盤加碼")
        elif sid in SP_V4:
            state = "持有（v4：出場照產業信）"
        else:
            state = "持有・未確認" + ("（上期未判、本期補判）" if js and js[-1]["judge"].startswith("未判") else "")
        if sid in SP_ENTRY_UP:
            state += "｜進場時已轉強"
        u, rr = val[sid]
        us, ua, ur = uv[sid]
        md.append(f"| {sid} {names.get(sid, '')} | {state} | {nj}／{SP_N_REPORTS} | {u} | {fpct(rr)} | {us:,} | {fnum(ua, 2) if us else '—'} | {fpct(ur)} |")
    md += ["", f"- 照規則合計（等額份數）：{tu} 份、累計 {fpct(tr)}（扣成本）、最大回落 {fpct(mdd)}（市值÷投入、未扣成本）"
           + (f"｜0050 還原（大盤報酬代理）同期 {fpct(bench)}" if bench is not None and np.isfinite(bench) else "")]
    for sid in SP_CODES:
        R = [r for r in rows if r["stock_id"] == sid]
        st = next((r for r in R if r["event"] == "起點買進"), None); ad = next((r for r in R if r["event"] == "轉強加碼"), None)
        f = lambda r: "—" if r is None else (f"{r['trade_date']} 開盤 {float(r['price_raw']):g}" if r["status"] == "成交" else f"{r['trade_date']} {r['status']}")  # noqa: E731
        if st is not None:
            md.append(f"- {sid}：起點 {f(st)}；加碼 {f(ad)}")
    for sid, note in SP_ENTRY_UP.items():
        md.append(f"- {sid} {names.get(sid, '')}：{note}")
    if df is not None:
        fl = []
        for sid in SP_SHORTAGE:
            rr = df[df["stock_id"] == sid]
            if len(rr):
                r = rr.iloc[0]; ph = r.get("pct_from_high")
                fl.append(f"{sid} ①營收月增 ≤ 0 連 2 月 {'是' if T(r.get('flag_mom2')) else '否'}、②距一年高點 ≤ −30% "
                          f"{'是' if (ph is not None and np.isfinite(ph) and ph <= F_DROP) else '否'}（{fpct(ph)}）")
        if fl:
            md.append(f"- 缺貨型{'、'.join(SP_SHORTAGE)} 旗標（只記、不賣；seq2 F①／F② 賣法作廢；缺貨型出場測試：無較佳賣法（10/22，暫定）⇒ 確認後照抱）：" + "；".join(fl))
    rm = [r for r in rows if r["event"] in ("新候選通知", "提醒")]
    if rm:
        md.append("- 小部位通知紀錄：" + "；".join(f"{r['report_asof']} {r['judge_detail'].strip()}" for r in rm))
    js = [r for r in rows if r["event"] == "月報判定"]
    if js:
        last = max(r["report_key"] for r in js)
        md.append(f"- {last} 月報判定：" + "；".join(f"{r['stock_id']} {r['judge']}（{r['note']}；{r['judge_detail']}）" for r in js if r["report_key"] == last))
    us = [r for r in urows if pd.Timestamp(r["trade_date"]) <= asof]
    if us:
        md.append("- 使用者實際成交：" + "；".join(f"{r['stock_id']} {r['event']} {r['trade_date']} {int(float(r['shares'])):,} 股（{r['detail']}；{r['note']}）" for r in us))
    return md + [""]


def sp_judgments(df, key, asof, P):
    J = {}
    for _, r in df[df["stock_id"].isin(SP_CODES)].iterrows():
        det = (f"近3月年增 {p0(r.get('yoy3'))}、近12月 {p0(r.get('yoy12'))}、加速 {fpct(r.get('accel'), True)}、"
               f"24月新高 {'是' if T(r.get('hi24')) else '否'}（上期 {'是' if T(r.get('hi24_prev')) else '否'}）")
        detp = (f"近3月年增 {p0(r.get('yoy3_prev'))}、加速 {fpct(r.get('accel_prev'), True)}、"
                f"24月新高 {'是' if T(r.get('hi24_prev')) else '否'}（上上期 {'是' if T(r.get('hi24_prev2')) else '否'}）")
        J[r["stock_id"]] = {"up": T(r.get("up")), "up_prev": T(r.get("up_prev")), "judged": r.get("rev_period") == P, "det": det, "det_prev": detp}
    return [(key, asof, J)]


def sp_bench(adj_df, asof, cal):
    """0050 還原（含息）自小部位起點開盤到資料日收盤（大盤報酬代理）；起點未到 ⇒ None。"""
    d0 = cal[cal >= pd.Timestamp(min(SP_CANDS.values()))]
    if not len(d0) or d0[0] > asof:
        return None
    df = adj_df("0050")
    return float(df["close"][df.index <= asof].dropna().iloc[-1] / df.at[d0[0], "open"] - 1)


def sp_paths():
    return os.path.join(FWD, "smallpos.csv"), os.path.join(FWD, "smallpos_user.csv")


USER_SELL = os.path.join(FWD, "user_sell.csv")    # 使用者指示賣出（stock_id,sell_date,reason,source）：sell_date＝預定開盤賣出日；前一晚通知、當天開盤記賣出
LAMP2 = os.path.join(FWD, "lamp2.csv")            # seq8 新需求型燈2：產業分析線每次判燈2 都寄信（附網址、日期）⇒ 回測線照信補一列（stock_id,lit_date,mail,url,note）


def user_sell_load(p=None):
    """{代號: (預定賣出日, 理由, 出處)}；檔不在 ⇒ {}。"""
    p = p or USER_SELL
    if not os.path.exists(p):
        return {}
    return {r["stock_id"]: (pd.Timestamp(r["sell_date"]), r.get("reason", ""), r.get("source", ""))
            for r in pd.read_csv(p, dtype=str, keep_default_na=False, encoding="utf-8-sig").to_dict("records")}


def lamp2_load(p=None):
    """{代號: (亮燈收信日 Timestamp, 信名, 網址)}；同檔多列取最早（只加一次）。檔不在 ⇒ {}。"""
    p = p or LAMP2
    if not os.path.exists(p):
        return {}
    out = {}
    for r in pd.read_csv(p, dtype=str, keep_default_na=False, encoding="utf-8-sig").to_dict("records"):
        d = pd.Timestamp(r["lit_date"])
        if r["stock_id"] in SP_NEWDEMAND and (r["stock_id"] not in out or d < out[r["stock_id"]][0]):
            out[r["stock_id"]] = (d, r.get("mail", ""), r.get("url", ""))
    return out


def remind_desc_fn(H, cal, sha):
    """seq6 250／625 日提醒的三項描述（只在提醒到期時才讀資料，平常不花時間）：
    ①同業擴產或復產消息：本模組無新聞資料 ⇒ 寫「見產業分析線燈號表」；②營收年增是否從確認後高點連 3 月下降；③股價距確認後最高收盤 %（還原收盤）。"""
    cache = {}

    def fn(sid, cf, asof):
        parts = ["同業擴產／復產：見產業分析線燈號表"]
        try:
            if "L" not in cache:
                cache["L"] = load_rev_pit(ensure_rev(asof_commit(sha, asof)[0]))[0]
            L = cache["L"]
            p0 = str(pd.Period(cf["report_key"], freq="M") - 1)             # 確認那份月報的營收期別
            x = L[(L["stock_id"] == sid) & (L["period"] >= p0)].copy()
            x = x[[pub10(q) < asof for q in x["period"]]].sort_values("period")
            y = (x["rev"] / x["ly"].where(x["ly"] > 0) - 1).values
            if len(y) >= 4 and np.isfinite(y).all():
                k = int(np.argmax(y)); dn = all(y[-j] < y[-j - 1] for j in (1, 2, 3)) and k <= len(y) - 4
                parts.append(f"營收年增自確認後高點連 3 月下降：{'是' if dn else '否'}（最新 {x['period'].iloc[-1]} {y[-1]:+.0%}、確認後最高 {y[k]:+.0%}）")
            else:
                parts.append("營收年增自確認後高點連 3 月下降：資料不足")
        except Exception as e:                                             # noqa: BLE001
            parts.append(f"營收年增：讀取失敗（{type(e).__name__}）")
        try:
            mk = pd.read_csv(os.path.join(H, "meta", "stocks.csv"), dtype=str).set_index("stock_id")["market"].to_dict()
            c = D.load_stock(sid, mk.get(sid, "twse"), cal).df["close"]
            c = c[(c.index >= pd.Timestamp(cf["report_asof"])) & (c.index <= asof)].dropna()
            parts.append(f"股價距確認後最高收盤 {c.iloc[-1] / c.max() - 1:+.0%}（還原）" if len(c) else "股價：資料不足")
        except Exception as e:                                             # noqa: BLE001
            parts.append(f"股價：讀取失敗（{type(e).__name__}）")
        return "；".join(parts)
    return fn


def sp_step(a, H, cal, asof, sha, names, judgments, write, now=None):
    """前瞻小部位：算新增列（含通知列：新候選、625 日提醒；write ⇒ 追加到 smallpos.csv；使用者實際欄檔不在 ⇒ 用情報 1000 信種子建檔）；
    回 (全部列, 新增列, 使用者實際列)。"""
    p, pu = sp_paths()
    rows = sp_load(p)
    now = now if now is not None else taipei_now()
    lp = lamp2_load(); us = user_sell_load()
    new = sp_update(rows, cal, asof, RawPx(H), judgments, names, str(now)[:19], sha, lamp2=lp, usell=us)
    closes = {s: raw_close(H, s, asof)[0] for s in SP_CODES}
    cfg = sp_cfg()
    ppi = ppi_loader(asof) if cfg.get(CFG_PPI) else None
    new += sp_notify(rows + new, cal, asof, H, closes, cfg, names, now, sha, ppi=ppi, lamp2=lp, desc=remind_desc_fn(H, cal, sha), usell=us)
    for k, r in enumerate(new):                    # seq 連號
        r["seq"] = str(len(rows) + k + 1)
    if write and new:
        os.makedirs(FWD, exist_ok=True)
        hdr = not os.path.exists(p)
        pd.DataFrame(new, columns=SP_COLS).to_csv(p, mode="a", header=hdr, index=False, encoding="utf-8-sig" if hdr else "utf-8")
    if write and not os.path.exists(pu):
        for r in USER_SEED:
            user_add(pu, r)
    urows = user_load(pu) if os.path.exists(pu) else [dict(r) for r in USER_SEED]
    return rows + new, new, urows


# ═════════════ 主程式 ═════════════
def prune_work(keep, n_keep=3):
    """~/bigrunwork 的 rev_／fund_ 快取（每份約 80MB）各留最近 n_keep 份＋本次用的；⛔ 只動 ~/bigrunwork。"""
    for pre in ("rev_", "fund_"):
        ds = sorted((d for d in os.listdir(WORK) if d.startswith(pre) and not d.endswith(".tmp")),
                    key=lambda d: os.path.getmtime(os.path.join(WORK, d)), reverse=True) if os.path.isdir(WORK) else []
        for d in ds[n_keep:]:
            if d not in keep:
                subprocess.run(["rm", "-rf", os.path.join(WORK, d)], check=False)


def write_out(md_lines, md_path, csvs, meta, meta_path):
    os.makedirs(os.path.dirname(os.path.abspath(md_path)), exist_ok=True)
    for p, d in csvs:                              # G 表照 10/20 快照 %.6g；A～F、季加報 %.10g（營收千元不截位）
        d.to_csv(p + ".tmp", index=False, encoding="utf-8-sig", float_format="%.6g" if "_G169" in p else "%.10g"); os.replace(p + ".tmp", p)
    json.dump(meta, open(meta_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    with open(md_path + ".tmp", "w", encoding="utf-8") as fo:
        fo.write("\n".join(md_lines) + "\n")
    os.replace(md_path + ".tmp", md_path)


def run(a):
    t0 = time.time()
    sha = a.sha or git("rev-parse", "origin/main").strip()
    sha = git("rev-parse", sha).strip()
    H = ensure_snapshot(sha)
    D.DATA = H; RLP.H = H
    cal = D.load_calendar()
    asof = pd.Timestamp(a.asof) if a.asof else cal[-1]
    if asof not in cal:
        raise SystemExit(f"⛔ 資料日 {asof.date()} 不在 {sha[:10]} 的交易日曆（尾 {cal[-1].date()}）")
    cal = cal[cal <= asof]
    if asof == D.load_calendar()[-1]:
        px2330 = pd.read_csv(os.path.join(H, "stocks", "2330.csv"), usecols=["date"])["date"].max()
        if str(asof.date()) != px2330:
            raise SystemExit(f"⛔ 日曆尾 {asof.date()} ≠ 2330 價格尾 {px2330}")
    state_p = a.state or STATE
    st = pd.read_csv(os.path.join(H, "meta", "stocks.csv"), dtype=str).set_index("stock_id")
    nm = st["name"].to_dict(); mkt = st["market"].to_dict()
    if a.kind == "auto":
        stt0 = load_state(state_p)
        todo = due(asof, stt0)
        if not todo:
            print(f"未到期（資料日 {asof.date()}；月報鍵 {asof.strftime('%Y-%m')}、季加報鍵 {quarter_key(asof)}；首份 月報 {FIRST['月報']}、季加報 {FIRST['季加報']}）")
            allr, new, _ = sp_step(a, H, cal, asof, sha, nm, [], write=True)  # 前瞻小部位：每晚都看（起點補記、加碼、放棄賣出）
            print(f"小部位前瞻：新增 {len(new)} 列" + ("：" + "；".join(f"{r['stock_id']} {r['event']} {r['status'] or r['judge'] or r['note'][:12]}" for r in new) if new else ""))
            if a.md:
                # 每日名單第十二節：只出現在「產出那個資料日」的名單（同資料日重產名單 ⇒ 從存檔補回，冪等）；其他資料日 ⇒ 移除
                secs = [open(e["daily節"], encoding="utf-8").read().rstrip("\n").split("\n")
                        for kind in ("月報", "季加報") for e in stt0.get(kind, {}).values()
                        if e.get("資料日") == str(asof.date()) and e.get("daily節") and os.path.exists(e["daily節"])]
                secs += sp_event_secs(sp_night_lines(allr, asof, nm))       # 小部位通知（新候選、625 日、報價；設定「小部位_LINE」開才有）
                put_daily(a.md, secs)
                print(f"名單第十二節：{'寫入 ' + str(len(secs)) + ' 節（同資料日已產者補回／新候選起點）' if secs else '無（已移除舊節）'}")
            return 0
    else:
        todo = [(a.kind, asof.strftime("%Y-%m") if a.kind == "月報" else quarter_key(asof))]
    ac, act = asof_commit(sha, asof)
    log(f"[版本] sha {sha[:10]}｜資料日 {asof.date()}｜截止版本 {ac[:10]}（{act}）｜要產 {todo}")
    MD = ensure_rev(ac); FD = ensure_fund(ac, sha)
    if FUND_NOTES:
        log(f"[財報] ⚠ {FUND_NOTES}")
    produced = []
    sp_new_all = []; sp_rows = []; newcand_done = False
    adj_cache = {}

    def adj_df(sid):
        if sid not in adj_cache:
            adj_cache[sid] = D.load_stock(sid, mkt.get(sid, "twse"), cal).df
        return adj_cache[sid]
    G = L = ldiag = corr = None
    for kind, key in todo:
        if kind == "月報":
            if L is None:
                L, ldiag = load_rev_pit(MD)
                corr = load_corrections(MD, set(POOL169) | {c for *_, c in af_codes()}, cutoff_of(asof))
                log(f"[月營收] {ldiag}；更正標註 {len(corr)} 格")
            G = build_g(asof, cal, H, FD, a.procs, L if a.g_rev == "pit" else None)
            df, md, P, sec = month_report(asof, sha, ac, act, H, L, ldiag, corr, G, cal, key)
            # 前瞻小部位：本份月報判定 ⇒ 新增列（auto 才寫檔；手動乾跑只試算）；月報加一節（放在 G 表之前）
            allr, new, urows = sp_step(a, H, cal, asof, sha, nm, sp_judgments(df, key, asof, P), write=(a.kind == "auto"))
            sp_new_all += new; sp_rows = allr
            gi = next(i for i, x in enumerate(md) if x.startswith("## G "))
            md = md[:gi] + sp_section(allr, urows, asof, adj_df, RawPx(H), nm, a.kind != "auto", df, sp_bench(adj_df, asof, cal)) + md[gi:]
            if sp_line_on():                       # 設定檔「小部位_LINE」＝true 才在 LINE 摘要加事件行（不計入 4 行）
                closes = {s: raw_close(H, s, asof)[0] for s in SP_CODES}
                ev = sp_events_report(new, closes, sp_cfg()) + sp_night_lines(allr, asof, nm)
                md = insert_line_events(md, ev); sec = insert_line_events(sec, ev)
                newcand_done = True
        else:
            df, md, sec = quarter_report(asof, sha, ac, act, FD, key, nm)
        if a.kind == "auto":
            base = os.path.join(FWD, f"{key}_{kind}")
            md_main = base + ".md"
        else:
            if not a.out:
                raise SystemExit("⛔ --kind 月報／季加報 要給 --out")
            md_main = a.out
            base = os.path.splitext(a.out)[0]
        csvs = [(base + ".csv", df)]
        if kind == "月報":
            csvs += [(base + "_G169.csv", G["df"]), (base + "_G169_missing.csv", G["missing"])]
        meta = {"種類": kind, "鍵": key, "資料日": str(asof.date()), "sha": sha, "截止版本": ac, "截止版本時間": str(act),
                "截止": str(cutoff_of(asof)), "產出時間": str(pd.Timestamp.now(tz=TZ)), "csv": [p for p, _ in csvs], "md": md_main,
                "g_rev": a.g_rev if kind == "月報" else None, "月營收期別": P if kind == "月報" else None}
        meta["daily節"] = base + "_daily節.md"
        write_out(md, md_main, csvs, meta, base + "_meta.json")
        with open(meta["daily節"], "w", encoding="utf-8") as fo:
            fo.write("\n".join(sec) + "\n")
        outs = [md_main]
        if a.kind == "auto" and a.out:
            o = a.out if len(todo) == 1 or kind == "月報" else os.path.splitext(a.out)[0] + "_季加報.md"
            os.makedirs(os.path.dirname(os.path.abspath(o)), exist_ok=True); shutil.copyfile(md_main, o); outs.append(o)
        produced.append((kind, key, outs, meta, sec))
        print(f"產出 {kind}：{outs[-1]}")
    if a.kind == "auto" and not any(k == "月報" for k, _ in todo):
        sp_rows, sp_new_all, _ = sp_step(a, H, cal, asof, sha, nm, [], write=True)
    if a.kind == "auto":
        print(f"小部位前瞻：新增 {len(sp_new_all)} 列" + ("：" + "；".join(f"{r['stock_id']} {r['event']} {r['status'] or r['judge']}" for r in sp_new_all) if sp_new_all else ""))
    prune_work(keep={f"rev_{ac[:10]}", f"fund_{ac[:10]}"})
    if a.kind == "auto":
        stt = load_state(state_p)
        for kind, key, outs, meta, _ in produced:
            stt.setdefault(kind, {})[key] = {"資料日": meta["資料日"], "sha": sha[:10], "md": outs[0], "daily節": meta["daily節"], "時間": meta["產出時間"]}
        save_state(state_p, stt)
    if a.md:                                       # 每日名單第十二節（整節置換、接檔尾、冪等）
        # auto ⇒ 整個第十二節換成今晚產的；手動 --kind ⇒ 只換同種類那節（另一種保留）
        put_daily(a.md, [p[4] for p in produced] + (sp_event_secs(sp_night_lines(sp_rows, asof, nm)) if a.kind == "auto" and not newcand_done else []),
                  SEC_PREFIX if a.kind == "auto" else SEC_PREFIX + a.kind)
        print(f"名單第十二節：寫入 {len(produced)} 節 ⇒ {a.md}")
    log(f"[完成] {len(produced)} 份｜{time.time() - t0:.0f}s")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--asof"); ap.add_argument("--sha"); ap.add_argument("--out")
    ap.add_argument("--kind", default="auto", choices=["auto", "月報", "季加報"])
    ap.add_argument("--procs", type=int, default=3); ap.add_argument("--g-rev", default="pit", choices=["pit", "hist"])
    ap.add_argument("--state", help="測試用：state.json 路徑")
    ap.add_argument("--md", help="每日名單 md：到期產出 ⇒ 寫入「## 十二、大漲觀察…」節；未到期 ⇒ 同資料日已產者補回、否則移除舊節")
    ap.add_argument("--user-add", help="使用者實際欄補記一列（只追加）：\"代號,名稱,事件,成交日,股數,均價,明細,來源,註\"（事件＝起點買進／轉強加碼／放棄賣出；賣出股數為負）")
    ap.add_argument("--fwd", help="測試用：forward 夾（state 以外的產出、smallpos*.csv）改寫到這裡")
    a = ap.parse_args()
    if a.fwd:
        global FWD
        FWD = a.fwd
    if a.user_add:
        v = [x.strip() for x in a.user_add.split(",")]
        if len(v) != len(USER_COLS) or v[2] not in (*BUY_EV, *SELL_EVS) or v[0] not in SP_CANDS:
            raise SystemExit(f"⛔ --user-add 要 {len(USER_COLS)} 欄 {USER_COLS}，事件 ∈ {(*BUY_EV, *SELL_EVS)}、代號 ∈ {SP_CODES}")
        pd.Timestamp(v[3]); int(v[4]); float(v[5])
        pu = sp_paths()[1]
        if not os.path.exists(pu):
            for r in USER_SEED:
                user_add(pu, r)
        user_add(pu, dict(zip(USER_COLS, v)))
        print(f"使用者實際欄已補記：{v}")
        sys.exit(0)
    try:
        sys.exit(run(a))
    except SystemExit:
        raise
    except Exception as e:                       # 失敗只 exit 非 0（不影響別的流程）
        traceback.print_exc()
        print(f"失敗：{type(e).__name__}: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

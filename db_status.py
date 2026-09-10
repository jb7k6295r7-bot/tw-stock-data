#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""資料庫現況總表 —— 一支腳本回答「現在有什麼、缺什麼」。

★ 為什麼要有這一支（2026-09-08）
────────────────────────────────
在這之前，要回答「資料庫還缺啥」得臨時拼十幾次查詢：讀 capital.csv 算空白、
讀 industry.csv 比對覆蓋、去猜哪個檔存不存在。**每次都重做一遍，而且每次拼法不同。**

這支把那些查詢固定下來。**它不抓網路、不改任何資料**，只讀 `data/` 然後印一頁。

⚠ 它報的是**資料庫現況**，不是「這一趟做了什麼」。
   `--fill`／`--resume`／狀態帳本都在這件事上騙過人：
   摘要說「0 失敗」而實際還有 5 個洞，因為它報的是那一趟碰到的東西。

用法
────
    python3 db_status.py              # 印出來
    python3 db_status.py --write      # 另外寫進 data/meta/_db_status.md

輸出的四段：
  ① 各層有多少、到哪一天
  ② 已知缺口（**寫死在 EXPECT 裡的預期值，對不上就標出來**）
  ③ 最近一輪各支腳本的檢查結果（讀 _last_run.md）
  ④ 完全沒有來源的東西（這一段是人維護的清單，不是算出來的）
"""
import argparse
import collections
import csv
import glob
import io
import json
import os
import sys
from datetime import datetime, timedelta, timezone

TPE = timezone(timedelta(hours=8))
DATA = "data"
META = os.path.join(DATA, "meta")
OUT = os.path.join(META, "_db_status.md")

# ★ 預期值。**對不上就會被標出來**，不是拿來當說明文字。
#   數字是 2026-09-08 的實測值；資料本來就會長，所以只檢查「不可以變少」。
EXPECT = {
    "stocks": 2100, "stocks_inst": 2600, "stocks_margin": 2400, "stocks_per": 2100,
    "adj": 2100, "daily": 2800,
    # ⛔ esb 不是全市場母體，是**逐檔逐月**抓的追蹤清單
    #   （`backfill.py` 的 `esb_month_url(code, ym)`，一檔一個檔案）。
    #   原本期望值寫 300，是拿「興櫃有幾百檔上市」去比「我們追蹤了幾檔」，
    #   於是永遠掛著一個 ★ 而那個 ★ 沒有任何意義。
    #   2026-09-09 實測目錄裡是 5267／6434／7879 三檔，各 147~2,844 列，
    #   而且**連無成交日都有列**（price_basis="無成交"），與 daily 不同。
    #   → 期望值改成「至少有 1 檔」：真正該擋的是「一檔都沒有」。
    "esb": 1,
}

# ④ 這一段是人維護的。**算不出來的東西不要假裝算得出來。**
# ⚠ 這一節列的是「找不到來源」。**另一類完全不同的風險**在
#   `freshness_check.py`：官方只保留一段時間、**不累積就永久失去**的那幾份
#   （集保一年、行事曆一年、快照只給當期）。⛔ 那不是「缺口」，是**死線**。
PROVEN_DEAD = [
    # ⛔ 這一節每一列都**必須附證據**：試過哪些端點、官方頁面怎麼說。
    #   沒有證據的一律歸下面那一節。
    #   ⚠ 2026-09-09 逐條複查後**這一節是空的**——那不是漏寫，是照規矩來的結果：
    #     現有每一條都還有沒試過的路（探針正在量），所以一條都不夠格宣告死路。
    # ★ 2026-09-09 下午出現本節第一列。它夠格的理由是**官方文件自己寫的保存期限**，
    #   不是「我試了很多次都失敗」——後者永遠只能寫成「我方取不到」。
    "⛔ **集保股權分散表：超過一年的歷史官方本來就不留**（不是我方抓不到）。"
    "證據是集保「附件一 持股分級表」PDF 的說明第 3 條，原文："
    "「本歷史檔案資料自 97 年 7 月份起建置，**資料保存期間為一年**。」"
    "（檔案逐字存在 `data/meta/sources/tdcc_holding_level_appendix1.pdf`，"
    "由使用者 2026-09-09 提供。）"
    "⇒ 查詢頁列 **51 個週別**不是被我方擋住的上限，**那就是全部**。"
    "⇒ 我方先前 12 條否定（token／日期欄名／stockNo／Referer／Cookie／method…）"
    "**問錯問題了**：那些在找「怎麼把兩年前的撈出來」，而兩年前的已經不存在。"
    "⇒ **這一列不是壞消息而是死線**：今天沒抓的，一年後永久失去 ⇒ "
    "`data/tdcc/` 的每週累積是唯一解，⛔ 那支 workflow 停掉就是**不可回復**的損失。",
]

# 尚未取得（還可以找）——每一列要附**下一步**：還沒試過什麼。
NOT_YET = [
    # ⚠ 面額變更那兩條 2026-09-09 已經收掉，移出本清單（本清單只列「還沒有來源的」）。
    #   沿革留在 docs/READ_CONTRACT.md 與 adjust.py 的 BOUNDS 旁，不在這裡重複。
    "⚠ **上櫃面額變更：數字已有官方獨立佐證，但『自動取得』還沒有**"
    "（2026-09-09 下午更新）。使用者用瀏覽器把櫃買「變更股票面額恢復買賣參考價」"
    "頁面匯出成 CSV 給我方（原檔存 `data/meta/sources/`，"
    "轉檔後 `data/meta/otc_par_reference.csv`，14 筆）。"
    "⇒ `otcparvalue.py` 閘門 (c) 的逐筆對帳**當天做完：14/14 相符**"
    "（比法在價格空間、容差半分，因為官方參考價印到分為止；"
    "`par_change.csv` 那 14 列的 evidence 已升級成 `shares_int_mult+official_ref`）。"
    "⇒ 所以**數字這一層不再是推導的孤證**。"
    "⛔ 但**端點仍然是我方取不到**：這份是人工匯出的，"
    "**下一次有新事件不會自己進來**，而且這份只涵蓋 2019-09-09 起。"
    "下一步（還沒做的）：① 每次有新的上櫃面額變更，要有人重匯一次；"
    "② 真正的解仍然是能執行 js 的環境。"
    "以下是取得官方值之前的沿革，留著是因為它解釋了因子怎麼來的："
    "**因子是用股數倍率推導的，不是官方公告**"
    "（TWSE `change/TWTB8U` 只涵蓋上市，實測上市 2/2、上櫃 0/5；"
    "TPEx **openapi/swagger** 那 225 個端點裡沒有減資／面額／參考價——⚠ 但那**只說明那一層沒有**：我方每天在用的 `otcinst`／`otcper`／`otcmargin` 也一個都不在 swagger 裡，它們住在 `www/zh-tw/<path>?date=…` 那一層。2026-09-09 使用者提供了頁面層的三個候選（`announce/market/change/reference.html` 等），已排進 `tpex_probe.py` 第 8 節量）。"
    "四道閘門在 `otcparvalue.py`，輸出帶 `derived_from=shares_ratio`。"
    "⚠ 日後 TPEx 官方端點出現時**官方優先、不符報 ✗**",
    "✅ **上櫃減資：同一天下午就補上了**（`data/meta/otc_reduce_reference.csv`，官方 284 筆）。"
    "使用者用瀏覽器匯出櫃買「減資恢復交易參考價」⇒ `reduce_check.py` 逐筆對帳："
    "**相符 232、不符 0**；減資原因字串 **232/232 一致**；我方上櫃有而官方沒有 **0 筆**；"
    "官方有我方沒有的 6 筆裡，5 筆恢復買賣日在今天或未來（預告，不算漏抓），"
    "1 筆是**官方自己重複的列**（6109 把 1070925 重打成 1090925，六個數字完全相同；"
    "我方 2020-09-25 無跳價無停牌）。"
    "⛔ 但**端點仍然取不到**：這份是人工匯出，新事件不會自己進來 ⇒ "
    "`reduce_check.py` 的「官方有我方沒有」同時會在**匯出檔過期**時吵，這是刻意的。"
    "以下是補上之前的紀錄："
    "⚠ **`long_hole` 227 筆的成因：2026-09-09 分層後剩 6 筆要查**（原本全部 `cause=unknown`）。"
    "⛔ 它們不是同一種東西，合成一個「227」等於把 6 筆真的藏在 221 筆雜訊裡："
    "① **非普通股 139 筆**（ETF 40／DR 與其他 99）⇒ 不在回測母體，"
    "而且比值帶 `[0.55,1.8]` 對沒有漲跌幅限制的 ETF **本來就不適用**；"
    "② **普通股但冷門到沒成交 82 筆**（前 60 日中位量**中位數只有 3,000 股**）"
    "⇒ 這**不是資料缺口**，是「日檔只收當天有成交的證券」這個已知性質的必然結果；"
    "③ **流動性足夠卻停了幾十上百個交易日：6 筆** ⇒ 這才是要查的——"
    "4414 如興（缺 203 日）、1785 光洋科（158）、5481 新華（87）、"
    "6131 鈞泰（61）、1225 福懋油（53）、1591 駿吉-KY（27）。"
    "⚠ 這 6 筆**都不在 `suspend.csv` 裡**（227 筆裡只有 2 筆對得到）。"
    "⭐ 2026-09-09 傍晚查出原因，而且它是一個**新的來源缺口**："
    "`suspend.csv` 的兩個來源（`twse-TWTAWU`、`tpex-sprcHis`）收的都是**暫停交易**，"
    "10,034 列裡 **9,594 列是權證**（`sec_kind=其他`），普通股只有 **409 列** "
    "⇒ **我方沒有「長期停止買賣」的來源**，只有「暫停交易」。"
    "⚠ 這與 `feeds.py` 早就記過的那句是同一件事"
    "（『suspend.csv 收的是暫停交易、不含換發新股票的停止買賣』），"
    "差別是現在知道**它造成了 6 個查不出成因的洞**。"
    "⭐ 2026-09-09 傍晚已經去找了（`suspend_probe --set longhalt`），結果："
    "`zh/listed/violations/stop.html` 是**證交所的「停止買賣」公告頁**，"
    "關鍵字對得上（「停止買賣」3 次、「財務業務」2 次），"
    "⛔ **但它是 js 空殼**：11,845 bytes 裡中文只有 706 字、"
    "`<tr>` **0 個**、js 4 支、我方那 6 檔**一檔都沒出現**、日期 0 個。"
    "另一條我依站台慣例拼的 `/rwd/zh/listed/violations/stop` 回 747 bytes（空）。"
    "⇒ **這條也是「我方取不到」，⛔ 不是「證交所沒有」**——"
    "跟櫃買那三頁、跟集保查詢頁同一種：**東西在頁面上，卡的是 js**。"
    "⇒ 這是今天第四個卡在同一件事上的缺口（上櫃面額／上櫃休市日／集保歷史／停止買賣）。"
    "下一步：需要能執行 js 的環境。⛔ 仍然不要拿 `suspend.csv` 去補，那是另一種東西。"
    "⚠ 附一個**被否證的假設**，免得下一個人重試：我原本想用「復牌日成交量爆量」"
    "當佐證，實測倍數是 **0.1 ~ 3.1 倍**（1591 只有 0.1 倍）⇒ **不成立，不要用**。"
    "目前唯一一致的形狀是：6 筆裡 4 筆的跨洞比值落在 ±10%（+9.99% ×3、−9.86% ×1），"
    "⚠ 但那**還不足以下結論**，要有外部來源才算。分層每天印進 `_last_run.md`。",
    "⚠ **上櫃減資 217 筆沒有官方交叉核對**（2026-09-09 新發現的缺口，⛔ 先前沒人問過）。"
    "使用者提供 `reducation/TWTAUU` 的長區間形式後，第一次把減資拿去跟官方雙向對："
    "**① 官方有、我方沒有 0 筆**（上市這半完整、沒有漏抓）；"
    "② 我方有、官方沒有 232 筆，按市場拆是 **tpex 217 ＋ 不在 industry.csv 15，twse 0**"
    "⇒ 「TWTAUU 只收上市」這個解釋站得住，⛔ 我方**沒有**在上市那半編出多餘事件。"
    "⇒ 但那 217 筆上櫃減資的因子仍然**只有我方自己算的一個來源**，"
    "跟今天早上的上櫃面額變更是同一個形狀（後者已由使用者匯出的官方表補上）。"
    "下一步（還沒試過的）：找 TPEx 對應的減資恢復買賣參考價表——"
    "⚠ 那頁多半跟面額變更同一族，也就是**要能執行 js**。"
    "⚠ 另外那 15 筆「不在 industry.csv」既不是上市也不是上櫃（多半已下市），"
    "⛔ 不要併進上櫃那堆算。",
    "⛔ **上市的 `shares` 歷史序列：這個端點取不到**（2026-09-09 Actions 實測）。"
    "上櫃的 `shares` 每天都在日檔裡所以有逐日序列；上市沒有，只有 "
    "`opendata/t187ap03_L` 這種**快照**端點。"
    "實測三發（`出表日期=1140630`／`date=20250630`／對照組 `資料年月=11406`）"
    "**回應與不帶參數的逐位元組完全相同、出表日期都是 1150908**"
    "⇒ 參數被無視，只給當期。"
    "⚠ 判準是**內容有沒有變**，不是「有沒有回東西」——"
    "`TWT49U` 就是不吃 `date` 卻把它原樣回傳，害我方把當天的四列寫進 2015 年每一天。"
    "⇒ 從今天起 `capital.py` 會存快照（`data/universe/capital/`），"
    "所以**未來的**序列會自己長出來；過去的只能另尋來源。"
    "下一步（還沒試過的）：MOPS 的**股本形成表**（`t05st03` 那一族），"
    "⛔ 那是唯一還沒量過的路，不要拿本條當「不存在」的結論。",
    "籌碼集中度／大戶持股的**歷史**（2026-09-08 起每週累積："
    "`data/tdcc/`，集保 17 級分級，四道驗算全過）。"
    "⚠ 2026-09-09 更新：**「補不回來」的原因查清楚了，而且比原本以為的更硬**——"
    "不是端點不吃日期，是**官方只保存一年**（見上一節，有官方文件原文）。"
    "⇒ 級距文字也在同一天拿到了：`data/meta/tdcc_level.csv`（1~15 級距、"
    "16 差異數調整、17 合計），所以「400 張以上」這種定義現在寫得出來了。"
    "下一步（還沒做的）：把級距表接進讀取端，讓「大戶」有明確定義",
    "✅ **32／33 的中文名 2026-09-09 補上了：文化創意業／農業科技業**。"
    "來源是官方 **ISIN 證券編碼查詢**（吃 `industry_code` 參數，網址由使用者提供）。"
    "⛔ 三項判準全過才落地：① 32 與 33 回不同清單（交集 0）⇒ 參數生效；"
    "② 我方標 32 的 34 檔、33 的 7 檔**全部**落在對應清單裡；"
    "③ 該頁「產業別」欄相異值各只有一種。"
    "⇒ 這一條同時關掉興櫃那 11 檔沒有名稱的問題——**兩邊本來就是同一個缺口**。",
    # ⚠ 91（DR）已經不在這張清單裡：2026-09-08 查證它**不是類股**，
    #   是證券種類，見 READ_CONTRACT 產業別那一節。問錯問題不算缺資料。
    "「某一天到底有幾檔股票成交」的**帶寬**（判準本身 2026-09-08 有了："
    "`MI_INDEX` 漲跌家數 vs 日檔，見 `_breadth_audit.csv`。"
    # ⚠ 這個數字**每天都在動**。寫死的話它會安靜地過期，而引用它的人不會知道它舊了
    #   （2026-09-09 實測：這裡曾寫 1,401，當天下午已經是 2,001）。
    #   ⇒ 用佔位符，寫檔時現算。算不出來就寫「算不出來」，⛔ 不留上一次的值。
    "⚠ **回補進度 {BREADTH}**，不再是「只有五天」；"
    "但帶寬要等回補完成才訂——**事後看資料再訂門檻等於沒有門檻**，"
    "所以目前仍然只驗方向：日檔的普通股家數 ≥ MI_INDEX 的股票家數）",
    # ★ 2026-09-09 照 `tpex_probe.py` 第 10 節寫死的停止條件停在這裡，不再繞。
    "⛔ **上櫃休市日：端點我方取不到**（⚠ 不是「櫃買沒有」）。"
    "⚠ 2026-09-09 下午更新：這一列原本還包含「面額變更參考價」，"
    "**那半已經拿到了**（使用者瀏覽器匯出，見上面那一列）——"
    "⇒ 這證實了下面六條否定的診斷是對的：**東西在頁面上，卡的是 js**。"
    "⛔ 但休市日那半仍然沒有，六條否定原文照留："
    "三個官方頁面都在、關鍵字也對得上（`announce/market/change/reference.html` "
    "出現「恢復買賣」5 次、「參考價」4 次），但端點**不在 HTML 裡**："
    "① 我先前報的 `/zh-tw/service/data` 是**頁尾連結**（我自己太鬆的正則截出來的假命中，已撤回）；"
    "② 三頁載入的 **8 支 js 全是共用的**（jquery／gsap／global.js…），沒有頁面專屬的；"
    "③ inline script **3、3、2 段，沒有一段在組請求**；"
    "④ `global.js` 只有泛用的 `_get_json(func, url, …)`，**url 是傳進去的參數**；"
    "⑤ 頁面的 `data-*` 帶的是**參數不是端點**"
    "（`data-format='D'/'csv'/'print'`、**`data-start='20190909'`** 是個日期）；"
    "⑥ **8 支 js 沒有一支提到 `data-format`／`data-start`** ⇒ 處理那些屬性的程式不在載入清單裡。"
    "**⇒ 在不執行 js 的前提下這條路走不通。** "
    "下一步（還沒試過的）：需要能執行 js 的環境，或走櫃買的資料訂閱管道；"
    "⚠ 頁面還有 Cloudflare 挑戰，找到端點也不代表打得通",
    # ⚠ 2026-09-09 複查：這一條先前記成「上櫃 131 檔股本空白」，**數字對、分類錯**。
    "⚠ **上櫃股本空白：真正的缺口是 8~9 檔，不是 131 檔**（2026-09-09 複查）。"
    "131 檔裡有 **123 檔是 ETF**（`00xxx`，其中 98 檔是債券 ETF）——"
    "**ETF 沒有「股本」這個概念**，它有受益權單位數（`shares` 欄有值）、沒有股本與面額。"
    "⭐ 2026-09-09 傍晚同一族又清掉一批：`capital.csv` 的 **mismatch 18 → 0**。"
    "原因是「股本 ＝ 股數 × 面額」對三種標的**整條不成立**，而我方一律標成 mismatch"
    "（那一欄的語意是『這一檔的股數不要拿去算佔股本比重』⇒ **等於叫下游別用一批正常資料**）："
    "① **無面額股 8 檔**（面額欄逐字寫「無面額」）⇒ 資本額÷股數是**平均發行價**不是面額"
    "（7812 稜研 25.018、6876 朗齊 16.864…）；"
    "② **外幣面額**（「美元 0.0010元」「美金0.05元」「港幣0.1元」）⇒ 資本額是新台幣，**不可相除**；"
    "③ **DR 6 檔** ⇒ 處理完前兩種之後剩下的 mismatch **全部是 DR**，"
    "比照代碼 91 那一條：**問錯問題**，不是資料異常。"
    "⛔ 三種的 note 分開寫（`no_par:`／`foreign_par:`／`dr:`），不合成一個「不驗」——"
    "理由不同，日後能不能補也不同。"
    "⚠ 並加了**負向測試**：一般新台幣面額而數字真的對不起來時**必須照樣 mismatch**，"
    "否則上面三條等於把這個訊號整個關掉。",
    "⇒ 那 123 檔是**問錯問題，不算缺資料**（比照 DR 91 的處理）。"
    "真正缺的是 8 檔普通股（4154 樂威科-KY、4183 福永生技、4950 金耘國際、5523 豐謙、"
    "6129 普誠、6624 萬年清、7757 金色三麥、8087 麗升能源）＋1 檔特別股（8349A 恒耀甲特），"
    "⛔ **2026-09-09 下午再更正一次：我上面那句『快照沒涵蓋到』是錯的診斷。**"
    "去 `data/universe/capital/tpex-mopsfin-O/1150908.csv` 逐檔查，"
    "那 8 檔普通股**全部都在裡面，連 `capital` 與 `par` 都有值**。"
    "真正的原因在我方：`load_universe()` **只讀最新那一個日檔**，"
    "而日檔**只收當天有成交的證券**（本庫已知陷阱）"
    "⇒ 成交稀疏的股票在任何一趟都可能不在母體裡，那一列就**永遠不會被重問**。"
    "佐證：同一天 4950、7757 補上了，正因為它們 09-08 剛好有成交；"
    "其餘 6 檔最後成交日是 09-02~09-04。"
    "⇒ 已改成取**最近 20 個交易日的聯集**（母體 2,719 → 2,761 檔）。"
    "✅ **2026-09-09 15:13 的 `capital.yml` 驗過了：那 8 檔普通股全部補上**"
    "（`source=universe:2026-09-08+tpex-mopsfin-O`）。"
    "⚠ 空白數字看起來只從 129 掉到 127，是因為同一個改動也把 42 個新代號帶進母體，"
    "其中不少是本來就沒有股本概念的 ETF／ETN——**不要看淨值，要看那 8 檔**。"
    "⚠ 而且這個改動**帶出兩個新的真缺口**："
    "① 8349A 恒耀甲特（特別股，不在上櫃名冊裡）；"
    "② 5371 中光電——最後成交 2026-08-21、**已不在上櫃名冊**，"
    "往回看 20 天才會撈到它。⛔ 我方沒有下市的獨立來源，"
    "所以只在輸出裡標「最後成交日不是最新那天」，**不宣告它下市**。"
    "⚠ 這條與集保、`_hist_status.csv` 是同一族的錯："
    "**去某處找不到，就說它不存在**——而三次都是我自己找的方式不對。",
    # ⚠ 同一輪複查刪掉兩條**已經不存在**的待辦：
    #   ①「487 檔有股本無產業別」→ 實際是 **364 檔而且全是興櫃**，
    #     而 `industry.py` 只涵蓋上市與上櫃 ⇒ 那不是缺口，是**興櫃沒有產業別來源**。
    #   ②「`_hist_status.csv` 6 筆待處理」→ ⚠ **2026-09-09 下午再更正一次：
    #     我上一次寫「那個檔根本不存在」是錯的**，它在 `data/mops/_hist_status.csv`
    #     （我先前只在 `data/meta/` 底下找）。真正的狀況是第三種：
    #     6 列 pending 全部是 **2026Q3 財報與 2026-09 月營收**——**還沒公告的期別**，
    #     所以 pending 是正確狀態，不是待辦。
    #     ⇒ 這是「去某處找不到，就說它不存在」的同一個錯，只是這次錯在我身上。
    #   ⇒ 兩條都是我自己 todo 上寫死、然後安靜過期的數字。與 breadth 那條同一族。
    "✅ **興櫃產業別：2026-09-09 下午補上了**（`data/meta/industry_esb.csv`，363 檔）。"
    "⭐ 來源一直都在，而且就在我們自己的 repo 裡——今天早上 `capital.py` 才開始"
    "保存端點原始快照，其中 `tpex-mopsfin-R`（興櫃公司名冊）就有 `SecuritiesIndustryCode`，"
    "363 檔**一個空值都沒有**。"
    "⇒ 這是今天第四次「去某處找不到就說它不存在」（前三次：集保、`_hist_status.csv`、上櫃股本）。"
    "★ 代碼可不可以共用上市上櫃那張名稱表**驗過才用**：拿上櫃名冊去對 `industry.csv`，"
    "**890 檔相同、0 檔不同**，而且這個檢查每趟重跑、掉下 100% 就報 ✗。"
    "⛔ 另存新檔不併進 `industry.csv`：那個檔在多處被當母體用，併進去會靜默改變那些判斷。"
    "⚠ 剩下的：363 檔裡 **11 檔沒有中文名，代碼是 32／33**——"
    "正是上櫃那兩個一直沒名稱的代碼，**兩個缺口其實是同一個**。"
    "下一步（還沒做的）：32／33 的中文名仍然只能從 TWSE 以外的地方找",
    "✅ **台股開休市行事曆（前瞻）2026-09-09 傍晚接上了**："
    "`www.twse.com.tw/rwd/zh/holidaySchedule/holidaySchedule?response=json`"
    "（網址由使用者提供）。實測 `stat=ok`、title「115 年市場開休市日期」、"
    "欄位 `['日期','名稱','說明']`、**27 列涵蓋 2026 整年含未來日期**。"
    "⇒ `holiday.py` 每天抓一次、**逐年累積**進 `data/meta/holiday_schedule.csv`。"
    "⛔ **限制：它只給當年**——`queryYear=2026`／`queryYear=115`／不帶參數"
    "三種回應**完全相同** ⇒ **拿不到明年的**，而年底正是最需要前瞻的時候。"
    "⇒ 所以要逐年存（跟集保只留一年同一種「不存就永久失去」，只是週期是一年）。"
    "⚠ 年底「今天之後 0 天」是**正常**的，⛔ 不寫成 ✗——"
    "那會每年 12 月底固定紅一次，然後大家學會忽略它；但那時"
    "**也不可以把「不在清單裡」當成「開盤」**。"
    "⚠ 這一條解的是**國定假日**那一半；颱風臨時休市走 `holiday.py` 的單向偵測。",
    "⭐ **翻案（2026-09-10）：上櫃交易日曆有官方歷史來源，我方原本那句是錯的。**"
    "市場情報分析線照全站選單找到櫃買的 `FMTQIK` 對應品："
    "`afterTrading/tradingIndex?date=<民國年/月>&response=json`，"
    "**一次回一個月的逐日列，至少回到 2011-01** ⇒ 2015-01-05～2026-08-31 完全涵蓋。"
    "⭐ 而且 104/01 的首列就是 104/01/05，自動證實 01-01 與 01-02 不是交易日，"
    "與我方日曆起點一致。"
    "⛔ **這一支的越界是「靜默回本月」**：97/01 與 94/01 都回 `stat:ok`，"
    "但 `date` 回 20260901、內容是當月的 7 列 ⇒ "
    "**必須檢查回應的 `date` 欄，不可以只看 `stat` 與列數**。"
    "⚠ 兩件不要假設：① 欄名在期間內改過（103/12 以前「成交股數（仟股）」、"
    "114/12 已是「成交張數」，**切換點未測**）；"
    "② **口徑未對**——同日這支給 832,664 張，`dailyQuotes` 表頭是 832,712,141 股，"
    "兩者不相等 ⇒ **判「哪一天有列」是安全的；拿它的金額當大盤成交值要先對口徑**。"
    "⇒ 下一步（還沒做的）：接成 `otc_calendar.py` 的歷史回補模式。"
    "以下是翻案前的紀錄，留著是因為它就是那個錯的形狀："
    "「上櫃的交易日曆**沒有獨立的外部來源**（FMTQIK 只有上市）。」"
    "⚠ 2026-09-09 做過一次全庫自我一致性檢查：2,847 個日檔裡"
    "「出現在日檔卻不在日曆」**0 天**、反方向也 0 天，週六 8 天兩邊一致，"
    "而且**不是循環自證**（backfill 逐平日迭代、與日曆無關）。"
    "⛔ 但那證明的是「我方資料自洽」，**不是「日曆對上櫃是對的」**——"
    "真正的外部判準仍然沒有。殘餘限制：週六預設不抓，"
    "「上櫃單獨開的週六場」兩邊都看不到（推論不存在，未經實測）。"
    "⚠ 2026-09-09 使用者指出正解：**對接櫃買官方的休市日公告**，"
    "並且另外留一個「臨時休市（颱風）」的機制。"
    "⭐ 這裡要分清楚兩半：颱風臨時休市**事後**我方看得出來"
    "（那天全市場日檔沒有成交），缺的是**事前**——「明天開不開盤」。"
    "⇒ 官方公告解的是前瞻那一半，已排進 `tpex_probe.py` 第 9 節量它在哪",
]


def now_tpe():
    return datetime.now(TPE)


def _rows(path):
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8", errors="replace") as f:
        return list(csv.DictReader(f))


def _count_dir(d, pat="*.csv"):
    return len(glob.glob(os.path.join(d, pat))) if os.path.isdir(d) else 0


def _span(rows, key):
    ds = sorted({r[key] for r in rows if r.get(key)})
    return (ds[0], ds[-1], len(ds)) if ds else ("—", "—", 0)


def section_layers(out):
    out.append("## ① 各層現況\n")
    out.append("| 層 | 檔／列 | 區間 | 預期 |")
    out.append("|---|---|---|---|")
    uni = os.path.join(DATA, "universe")
    layers = [
        ("價格 `data/stocks/`", os.path.join(DATA, "stocks"), "stocks"),
        ("三大法人 `data/stocks_inst/`", os.path.join(DATA, "stocks_inst"), "stocks_inst"),
        ("融資融券 `data/stocks_margin/`", os.path.join(DATA, "stocks_margin"), "stocks_margin"),
        ("本益比 `data/stocks_per/`", os.path.join(DATA, "stocks_per"), "stocks_per"),
        ("還原因子 `data/adj/`", os.path.join(DATA, "adj"), "adj"),
        ("興櫃 `data/universe/esb/`", os.path.join(uni, "esb"), "esb"),
    ]
    for label, d, key in layers:
        n = _count_dir(d)
        exp = EXPECT.get(key, 0)
        mark = "" if n >= exp else f" ★ 少於預期 {exp}"
        out.append(f"| {label} | {n} 檔 | — | {exp}+{mark} |")

    days = sorted(os.path.basename(p)[:-4]
                  for p in glob.glob(os.path.join(uni, "daily", "*.csv")))
    exp = EXPECT["daily"]
    mark = "" if len(days) >= exp else f" ★ 少於預期 {exp}"
    out.append(f"| 日檔 `data/universe/daily/` | {len(days)} 天 | "
               f"{days[0] if days else '—'} ~ {days[-1] if days else '—'} | {exp}+{mark} |")

    cal = _rows(os.path.join(META, "calendar_twse.csv"))
    if cal and days:
        k = list(cal[0].keys())[0]
        cs = {r[k] for r in cal}
        miss = sorted(set(cs) - set(days))
        out.append(f"| 交易日曆 `calendar_twse.csv` | {len(cs)} 天 | — | "
                   f"日曆有而日檔沒有：**{len(miss)} 天**"
                   + (f"（{'、'.join(miss[:5])}…）" if miss else "") + " |")
    out.append("")


def section_events(out):
    out.append("## ② 事件類與基本面\n")
    specs = [
        ("停牌 `suspend.csv`", "suspend.csv", "halt_date"),
        ("處置 `disposal.csv`", "disposal.csv", "start_date"),
        ("注意 `attention.csv`", "attention.csv", "date"),
    ]
    out.append("| 檔 | 列數 | 區間 | 市場 | 種類 |")
    out.append("|---|---|---|---|---|")
    for label, fn, dk in specs:
        r = _rows(os.path.join(META, fn))
        if not r:
            out.append(f"| {label} | **0（檔不存在或空的）** | — | — | — |")
            continue
        lo, hi, nd = _span(r, dk)
        mk = collections.Counter(x.get("market", "") for x in r)
        kd = collections.Counter(x.get("sec_kind", "") for x in r)
        empt = sum(1 for x in r if not x.get(dk))
        note = f"｜★ 空日期 {empt}" if empt else ""
        out.append(f"| {label} | {len(r)}{note} | {lo} ~ {hi}（{nd} 天）| "
                   f"{dict(mk)} | {dict(kd)} |")
    out.append("")

    cap = _rows(os.path.join(META, "capital.csv"))
    if cap:
        by = collections.Counter(x["market"] for x in cap)
        blank = collections.Counter(x["market"] for x in cap
                                    if not (x.get("capital") or "").strip())
        mis = [x for x in cap if (x.get("note") or "").startswith("mismatch")]
        odd = [x for x in mis if "*" not in x["name"] and "DR" not in x["name"]]
        out.append("**股本 `capital.csv`**\n")
        for m in sorted(by):
            out.append(f"- {m}：{by[m]} 檔，股本空白 {blank.get(m, 0)}")
        out.append(f"- mismatch {len(mis)} 檔"
                   + (f"，**其中 {len(odd)} 檔不帶 `*` 也不是 DR ★ 要查**" if odd
                      else "（全部帶 `*` 或 DR，屬已知限制）"))
        out.append("")

    ind = _rows(os.path.join(META, "industry.csv"))
    if ind and cap:
        ii = {x["stock_id"] for x in ind}
        cc = {x["stock_id"] for x in cap}
        noname = collections.Counter(
            (x["market"], x.get("industry_code", ""))
            for x in ind if not (x.get("industry_name") or "").strip())
        out.append("**產業別 `industry.csv`**\n")
        out.append(f"- {len(ind)} 檔；有股本但無產業別 {len(cc - ii)}、"
                   f"有產業別但無股本 **{len(ii - cc)}**")
        if noname:
            out.append("- 無中文名的代碼：" +
                       "、".join(f"{m} {c}（{n} 檔）" for (m, c), n in sorted(noname.items())))
        out.append("")

    hist = os.path.join(DATA, "mops", "_hist_status.csv")
    hr = _rows(hist)
    if hr:
        st = collections.Counter(x.get("status", "") for x in hr)
        out.append(f"**財報回補帳本 `_hist_status.csv`**：{len(hr)} 列 {dict(st)}")
        out.append("　⚠ 這個帳本記的是**上一趟碰到的期別**，不是資料庫現況。"
                   "要判斷有沒有洞得看 `data/mops/*_hist/` 本身。\n")


def section_lastrun(out):
    out.append("## ③ 最近一輪各支腳本\n")
    p = os.path.join(META, "_last_run.md")
    if not os.path.exists(p):
        out.append("（`_last_run.md` 還不存在——**沒有任何一支腳本用新版跑過**）\n")
        return
    txt = open(p, encoding="utf-8").read()
    bad = [ln for ln in txt.splitlines() if ln.startswith("- **✗**")]
    heads = [ln for ln in txt.splitlines() if ln.startswith("## ")]
    for h in heads:
        out.append(f"- {h[3:]}")
    if bad:
        out.append("\n**沒過的檢查：**")
        out += [f"  {x}" for x in bad]
    out.append("")


def _breadth_progress():
    """回補進度現算。⛔ 算不出來就說算不出來，不可以回一個舊的數字。"""
    try:
        # ⚠ 用 `__file__` 錨定，不用模組裡那個 `DATA = "data"`——那是**相對 CWD** 的，
        #   從別的目錄叫這支就會指到不存在的地方（runlog.py 有同一條註記）。
        root = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
        done = len(glob.glob(os.path.join(root, "universe", "breadth", "*.csv")))
        with io.open(os.path.join(root, "meta", "calendar_twse.csv"),
                     encoding="utf-8") as f:
            tot = max(0, sum(1 for _ in f) - 1)
        if not tot:
            return "算不出來（日曆是空的）"
        return f"{done:,}/{tot:,} 天（{done / tot:.0%}）"
    except OSError as ex:                                        # noqa: BLE001
        return f"算不出來（{type(ex).__name__}）"


def _brk_counts():
    """`breakpoints_unexplained.csv` 的兩節各幾列。

    ⛔ **分開報，不合計**（情報分析線 2026-09-09 10:45 的要求）：
      合成一個總數的話，其中一節歸零只會讓總數「變小一點」——
      看起來像正常波動，而那正是要防的失效形狀。
    """
    p = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                     "data", "meta", "breakpoints_unexplained.csv")
    try:
        with io.open(p, encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
    except OSError:
        return None
    c = collections.Counter(r.get("kind", "") or "(沒有 kind 欄)" for r in rows)
    return c


def section_nosource(out):
    # ★ 市場情報分析線 2026-09-09 10:45 裁定：這一節要分兩節，而且**命名用行動語態**。
    #   理由是我自己踩過的坑：上櫃停牌我猜了五個端點名全 404，就寫成
    #   「沒有來源、永遠補不回來」——**實際上它在 `bulletin/sprcHis`，是 POST**。
    #   那一次的傷害不是寫錯一行字，是**後面的人不再去找**。
    out.append("## ④ 來源狀態（人維護的清單，不是算出來的）\n")
    out.append("> ⛔ **「已證實無來源」這一節，每一列都必須附上證據；"
               "沒有證據的一律歸「尚未取得」。**")
    out.append("> **舉證責任在「宣告死路」的那一方，不在「還想找」的那一方。**\n")
    ctx = {"BREADTH": _breadth_progress()}
    c = _brk_counts()
    if c is None:
        out.append("- ⚠ `breakpoints_unexplained.csv` 讀不到")
    else:
        out.append("- `breakpoints_unexplained`："
                   + "｜".join(f"**{k} {v}**" for k, v in sorted(c.items()))
                   + "（⛔ 兩節分開報，不合計）")
    out.append("")
    out.append("### ④-1 已證實無來源（不要再花時間找）\n")
    if not PROVEN_DEAD:
        out.append("- （目前 0 列。⚠ **空的是正確狀態，不是漏寫**——"
                   "現有每一條都還有沒試過的路，所以一條都不夠格宣告死路。）")
    for x in PROVEN_DEAD:
        out.append(f"- {x}")
    out.append("")
    out.append("### ④-2 尚未取得（還可以找）\n")
    for x in NOT_YET:
        # ⚠ 只有帶佔位符的那幾條會被代入；其餘原文照抄。
        #   `format` 會把 `{` 當語法，所以只對真的含 `{X}` 的字串做。
        for k, v in ctx.items():
            x = x.replace("{" + k + "}", v)
        out.append(f"- {x}")
    out.append("")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    a = ap.parse_args()

    if not os.path.isdir(DATA):
        print("[db_status] 找不到 data/，要在 repo 根目錄跑", file=sys.stderr)
        return 1

    out = [f"# 資料庫現況　{now_tpe().isoformat(timespec='seconds')}（台北）", "",
           "**這一頁報的是資料庫現況，不是某一趟做了什麼。**", ""]
    section_layers(out)
    section_events(out)
    section_lastrun(out)
    section_nosource(out)
    text = "\n".join(out)
    print(text)
    if a.write:
        os.makedirs(META, exist_ok=True)
        with open(OUT, "w", encoding="utf-8") as f:
            f.write(text + "\n")
        print(f"\n[db_status] 寫出 {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

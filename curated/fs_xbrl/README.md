# 財報細項（MOPS IFRS XBRL 季度整包）2013Q1～2026Q2

⭐ 由 `build.py` 從 MOPS XBRL 季度整包建成；由 backfill.yml mode=curated 原樣複製到 `data/meta/fs_xbrl/`。
依據：情報 1013-2340（存貨／應收增速、營業現金流與淨利背離）；裁定 seq348 §三；本線 1015 探針。
營業成本／營業毛利／營業利益三欄：裁定 seq412 §四 Q-G、台股 seq533 C（2026-10-21 加，54 季全部重建）。

## 檔與欄

`fs_xbrl_<年>.csv`，一家一季一列。單位：**新台幣元**（已乘 XBRL 的 scale；⛔ 不是千元）。

| 欄 | 意義 |
|---|---|
| period, stock_id, period_end | 季別（2024Q1）、公司代號、期末日 |
| industry_template | XBRL 業別範本（ci 一般業、basi 銀行、bd 證券、ins 保險、fh 金控、mim…） |
| report | cr＝合併、ir＝個體（同季兩種都有時取合併） |
| inventories, accounts_receivable, accounts_receivable_related, notes_receivable | 存貨、應收帳款淨額、應收帳款－關係人淨額、應收票據淨額（期末餘額） |
| contract_liabilities_current／_noncurrent | 合約負債（流動／非流動）；⚠ IFRS 15，**2018 起**才有，之前空白是正常的 |
| cash, total_assets, total_equity | 現金及約當現金、資產總計、權益總計 |
| revenue_ytd, profit_before_tax_ytd, net_income_ytd | 營業收入、稅前淨利、本期淨利 ⚠ **年初至今累計** |
| cost_of_sales_ytd | 營業成本（合計）⚠ 年初至今累計。XBRL `tifrs-bsci-ci:OperatingCosts`（⛔ 不用 `ifrs-full:CostOfSales`：台灣範本裡那是子項「銷貨成本」） |
| gross_profit_ytd | **營業毛利（毛損）淨額**＝營業毛利 −未實現 ＋已實現銷貨損益 ⚠ 年初至今累計。新版 `ifrs-full:GrossProfit`、早年 .xml 版 `tifrs-bsci-ci:GrossProfitLossFromOperationsNet`（⛔ 不收未扣未實現前的 `GrossProfitLossFromOperations`，免得口徑混用） |
| operating_income_ytd | 營業利益（損失）⚠ 年初至今累計。新版 `ifrs-full:ProfitLossFromOperatingActivities`、早年 .xml 版 `tifrs-bsci-ci:NetOperatingIncomeLoss` |
| operating_cash_flow_ytd, depreciation_ytd, capex_ytd | 營業活動現金流、折舊、取得不動產廠房及設備（負數＝流出） ⚠ **年初至今累計** |
| source_file | 整包內的檔名 |

⚠ 三個新欄（cost_of_sales_ytd、gross_profit_ytd、operating_income_ytd）排在 capex_ytd 之後、source_file 之前；既有欄的位置不變。
⚠ `_ytd` 欄是累計數：Q2＝上半年。要單季請自己減前一季（Q1 本身就是單季）。
⚠ 某科目空白＝該家該季 XBRL 沒有這個科目（例：金融業沒有存貨），⛔ 不是 0。

## 範圍（2026-10-15 建置；2026-10-21 加三欄重建）

- 54 季全齊（2017Q2、2025Q2 第一次下載中斷，重抓後補齊）。
- 每季家數：Q1／Q3 約 1,530～2,050 家；Q2／Q4 約 1,930～2,700 家——**半年報與年報多了只交半年報、年報的公開發行公司**（未上市櫃）⇒ 研究上市櫃請先用本庫母體篩。
- 2026Q2 覆蓋例（共 2,679 家）：存貨 2,338、應收帳款 2,460、合約負債 1,918、營業現金流 2,667、稅前淨利 2,676。
- 2026-10-21 重建：既有欄 2,367,666 格與前版逐格相同（0 不同）；整包比前版多 4 列（晚交的 2024Q4 7912、2025Q4 7955／7956、2026Q2 7956）。
- **營業成本／毛利／營業利益：2013Q1 起每季都有**（一般業 ci）。每季 ci 覆蓋：成本 98.6～99.9%、毛利 99.2～100%、營業利益 99.9～100%（沒有的多半是報表本身沒有成本科目的公司，例：毛利＝營收的服務業、尚無營收的新藥公司；這時成本、毛利空白，⛔ 不是 0）。
- ⚠ **金融業（basi 銀行、fh 金控、ins 保險、mim）三欄一律空白**——報表沒有營業成本、毛利，這是正常的。
  ⚠ bd 證券：成本、毛利空白；營業利益 **2013Q1 起都有**——2017Q4 以前取 `tifrs-bsci-bd:NetOperatingIncomeLoss`、2018Q1 起取 `ifrs-full:ProfitLossFromOperatingActivities`（2017Q4 整包只有前者、2018Q1 只有後者，沒有重疊；2026-10-21 從同批整包重跑解析補上 2013～2017 共 1,163 筆）。
    抽 6005、2856、6024 看 2017Q4 單季（Q4 累計−Q3 累計）→2018Q1：9.1 億→9.7 億、2.4 億→4.0 億、1.1 億→3.8 億，數量級連續。

## 驗證

- 新三欄對 `data/mops/fs_hist`（ci，2015Q1～2026Q2，千元四捨五入）：成本 78,844 筆相符 78,839、毛利（淨額）78,931 筆相符 78,926、營業利益 79,008 筆相符 79,003；三欄的不符都是同樣 5 筆：6111（2025Q2～Q4）、3041（2025Q3、Q4）＝下面既有欄就已知的重編。另有 2 筆本表整列空白、簡明表有值（2021Q2 1519、2023Q3 6243：連營收、淨利都空白，前版就是這樣，context 對不上，⛔ 未另查）。
  抽 10 家（2330、1101、2317、1301、2454、2002、1216、2912、2308、2603）460 家季三欄全部相符。
- 2013～2014（簡明表沒有）：對 `data/mops/fin_hist` gp_ytd／opi_ytd（同一份 XBRL、另一支解析程式）毛利 13,146 筆、營業利益 13,171 筆全部相符——⚠ 同源，只證明解析一致，不是獨立來源。
- 恆等式 營收 − 成本 ＝ 毛利（ci，三欄都有 104,988 列）：完全相等 100,489（95.7%）、不等 4,499。不等列 |差|／營收 中位數 0.03%，98% 在 5% 以內；有簡明表可對的 3,602 列裡，3,416 列的差＝未實現／已實現銷貨損益（毛利取淨額的結果）、186 列是生物資產公允價值變動等列在毛利前的科目（例：1905、1907、1240）。剩下 897 列沒有簡明表可對（2015 前或未上市櫃），差最大的是 4712（2019 年，營收很小）。
- 對本庫 `data/mops/bs_hist`、`fs_hist`（MOPS 簡明表，一般業 ci）同期同公司比對 資產總計、權益總計、營業收入、稅前淨利 共 297,380 筆：**相符 297,358、不符 22**。
  不符全部集中在 6111（2025Q2～Q4）、3041（2025Q3）——推定為重編（整包與簡明表抓取時點不同版本），⛔ 未逐筆查證。
- 抽驗 2330：2013Q1 營收 1,327.5 億、營業現金流 735.7 億；2024Q1 營收 5,926.4 億、營業現金流 4,363.1 億、資本支出 1,813.0 億。

## ⚠ 用之前

- ⛔ **可用日不是期末日**：財報要等公告（Q1／Q2／Q3 約 45 天、年報約 90 天）。要可用日請對 doc.twse `t57sb01` 的上傳時戳（到秒），⛔ 用 period_end 會前視。
- 兩種原始格式：早期是純 XBRL（.xml，`ifrs:` 前綴、值不帶 scale），後來改 inline XBRL（.html，`ifrs-full:`、值×scale、負號在 sign 屬性）；程式兩種都讀。
- 非曆年制公司（會計年度不從 1 月開始）的累計欄會是空白（context 對不上），⛔ 未另處理。
- 來源：`https://mopsov.twse.com.tw/server-java/FileDownLoad?step=9&fileName=tifrs-<YYYYQn>.zip&filePath=/home/html/nas/ifrs/<YYYY>/`（每包約 10～80 MB；直接打 `/nas/ifrs/...zip` 回 403）。2012Q4 以前回 HTML＝沒有（IFRS 2013 起）。
- 新季別：目前是一次性回補，⛔ 還沒接排程（2026Q3 約 11 月中公告後由本線補跑 `--from 2026Q3 --to 2026Q3`）。

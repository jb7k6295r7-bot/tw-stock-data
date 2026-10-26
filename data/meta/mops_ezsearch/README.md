# MOPS 公告快易查（ezsearch）重大訊息原始欄位 2015-01～2020-12

⭐ 原樣存檔；由 backfill.yml mode=curated 複製到 `data/meta/mops_ezsearch/`。
依據：產業分析線 seq51；裁定 seq478 §三（公開資料，准進庫，撞頂窗清單照存）。抓取 2026-10-26（資料庫線）。

## 檔與欄
- `<YYYY-MM>.csv`（72 個月）：官方原欄位 CDATE（民國）, CTIME, COMPANY_ID, COMPANY_NAME, AN_CODE, AN_NAME, SUBJECT, CODE_NAME, TYPEK, HYPERLINK，加 fetched_at。
- `_summary.csv`：每月筆數、窗數、撞頂窗清單（全期撞頂 0 窗）。
- `recon_monthly.csv`、`recon_sample20.csv`：對公開庫 `data/mops/news` 的逐月對帳與 20 則逐欄抽核（20/20 相同）。

## 抓法
- POST `mopsov.twse.com.tw/mops/web/ezsearch_query`：`step=00`、`RADIO_CM=1`、`TYPEK=sii|otc`、`PRO_ITEM=M00`（只取重大訊息）、`SDATE`／`EDATE`。
- 上市與上櫃要分開打。⛔ 不帶 TYPEK 會出髒資料（每則重複 4～7 列、公發公司標成上市）。⛔ `CO_MARKET` 是產業碼，不是市場。
- 每發上限 1,000 列、超過會安靜截斷 ⇒ 沿用 `mops_probe.split_window_avoiding_cap` 切窗；725 窗，撞頂 0。

## 範圍：285,953 列
| 年 | 上市 | 上櫃 |
|---|---|---|
| 2015 | 27,383 | 15,104 |
| 2016 | 27,895 | 15,789 |
| 2017 | 29,038 | 16,862 |
| 2018 | 30,773 | 17,410 |
| 2019 | 32,115 | 18,328 |
| 2020 | 34,195 | 21,061 |

## ⛔ 使用限制（必讀）
1. **存活者偏差**：比 `data/mops/news`（sii＋otc）少 5～13%，越早年越少。
   - 缺的 25,305 則：已下市公司與 DR 整家不在（12,224 則），其餘是公司在 ezsearch 第一則之前的公告（13,008 則）。
   - ⇒ **母體一律用 `data/mops/news`**；這份只拿來補 AN_CODE／AN_NAME／HYPERLINK（以日期＋時間＋代號配對；兩邊都有的 285,878 則主旨全部一致）。
2. **CODE_NAME 是現在的產業別，不是公告當時的**：2015～2020 的公告上出現 2023 年後才有的類別（居家生活、運動休閒、綠能環保、數位雲端）。
   - TYPEK 很可能也是現在的市場別。
   - ⇒ 當時產業別請用 `data/meta/industry_hist/`。
3. CTIME 空白 72 列，配不上 news 的鍵。
4. HYPERLINK 指向重訊明細頁 `ajax_t05sr01_1`（每則 1 發），也可用 news 的日期＋時間＋代號＋序號自己組；已下市公司也取得到，DR 回空殼。

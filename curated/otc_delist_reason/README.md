# 上櫃終止上櫃原因（官方分類）

⭐ 由 backfill.yml mode=curated 原樣複製到 `data/meta/otc_delist_reason/`。起因：台股地雷股濾網 seq1 a（2026-10-07）。

## 來源
TPEx `https://www.tpex.org.tw/www/zh-tw/company/deListed?code=&date=ALL&reason=<k>&id=&response=json&paging-offset=0&paging-size=5000`
⭐ `reason` 參數本身就是官方分類：0 被合併｜1 金控｜2 轉上市｜3 取消第二類股｜4 拒絕往來｜5 其他｜6 管理股票（7、8 回全部 582 筆，不用）
0～6 合計 582 筆＝全部（2026-10-07 實測）。build.py 本機跑 7 發、每發間隔 3.5 秒。

## 欄位
delist_date（西元）, stock_id, name, reason_code, reason_label, rule_text（官方「終止上櫃原因」欄原文；多為法規條號）

## 驗收
- 與 `data/meta/delisted.csv` 上櫃 240 筆：240／240 全對上（代號與日期）；其餘 342 筆是轉上市（庫內另存 otc_to_twse.csv）
- 官方原檔有兩筆代號帶空白（'\t3126'、'1752 '）⇒ 已去空白
- 2015 起：被合併 51、其他 28、轉上市 27、拒絕往來 3、管理股票 1

## ⚠ 讀法
- 「其他」混著【自願申請終止】（股東會／董事會決議）與【財務性】條款 ⇒ 要再拆請對照 rule_text 原文與櫃買業務規則條文；本線⛔ 沒有推測條號意義
- 下市日是事後標籤，⛔ 不是事前可用的訊號
- 上市沒有對應的原因欄（TWSE suspendListing 與 reportIndex 只有日期、名稱、代號）

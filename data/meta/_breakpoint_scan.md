# breakpoint_scan 的輸出（全母體斷點掃描＋與 par_change.csv 對帳）
# 規則屬回測線／K線線，這裡只是把它接進每日管線。
# 產生方式：python3 breakpoint_check.py

```
附表 holes_scan.csv：缺 ≥ 5 日且無事件的洞 1403 個、174 檔；其中 liq_ok 10 個（＝ 進斷點清單的 gap 規則）
母體 2130 檔，斷點 12 個、11 檔
rule
gap          9
price+gap    3
missing_trading_days 分布： {'min': 6.0, '50%': 59.5, 'max': 218.0}

對帳 par_change.csv：24 筆／22 檔 → 已有因子 24、仍為斷點 0、漏抓 0
規則另外抓到（不在 par_change.csv）：12 個、11 檔；其中 price 規則 3 個
stock_id market       date  prev_date  ratio  missing_trading_days      rule
    1225   twse 2025-06-23 2025-04-02 1.0995                    53       gap
    1591   tpex 2026-07-22 2026-06-10 1.0995                    27       gap
    1785   tpex 2017-01-03 2016-05-16 1.0994                   158       gap
    2929   twse 2021-05-04 2021-04-06 1.0992                    18       gap
    4414   twse 2023-06-26 2022-08-17 1.0993                   203       gap
    4415   tpex 2017-11-22 2017-04-11 2.4790                   156 price+gap
    5481   tpex 2025-09-19 2025-05-19 0.9014                    87       gap
    6131   twse 2016-07-05 2016-04-06 1.0741                    61       gap
    6131   twse 2019-04-10 2018-05-17 0.2562                   218 price+gap
    8101   twse 2024-11-19 2024-08-21 5.5000                    58 price+gap
    8105   twse 2026-08-27 2026-08-18 1.0978                     6       gap
    9136   twse 2026-05-19 2026-04-22 0.9630                    17       gap
```

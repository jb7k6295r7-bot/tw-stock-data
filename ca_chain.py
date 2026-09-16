# -*- coding: utf-8 -*-
"""補上 **TPEx 漏送的憑證鏈**。⛔ 這一支**不降低**任何驗證。

## 事實（2026-09-13 在 Actions 上實測，⛔ 不是本機——本機對交易所一律 403）

```
TPEx  www.tpex.org.tw   對方送 **1 張**（只有葉憑證）  Verify return code: 21
TWSE  www.twse.com.tw   對方送 **3 張**（完整）        Verify return code: 0
⭐ 而兩者的葉憑證發行者**完全相同**：TWCA SSL Certification Authority
```

⇒ **是 TPEx 這一站漏送中間憑證**，⛔ 不是我方 CA 太舊
（系統 CA 與 `certifi` **兩份都不通**，而 TWSE 兩份都通）。
⚠ 瀏覽器看不出來，因為瀏覽器會自己照 AIA 去把中間憑證抓回來補上（AIA chasing）。
⭐ 這一支做的就是同一件事，只是**離線**做。

## ⛔⛔ 為什麼這**不是**「把驗證關掉」

補進來的兩張憑證**自己不會產生信任**——它們只是「路」。
鏈仍然必須走到一個**系統本來就信任的根**才算數：

```
www.tpex.org.tw
  └─ TWCA SSL Certification Authority   ← 補這張（TPEx 漏送）
       └─ TWCA CYBER Root CA            ← 補這張（交叉憑證）
            └─ TWCA Global Root CA      ← ⭐ **系統信任庫裡本來就有**
```

⚠ 少了第二張是不夠的：`TWCA CYBER Root CA` **不在**信任庫裡
（庫裡只有 `TWCA Global Root CA` 與 `TWCA Root Certification Authority`）
——⛔ 我第一版只補了中間憑證，本機一驗就發現接不上。
⭐ 這兩張是**照抄 TWSE 送的那一組**（它在 runner 上驗得過 ⇒ 那組是夠用的），
⛔ 不是我憑 AIA 猜的。

離線驗過（⛔ 不連網）：`openssl verify -untrusted certs/tpex_chain.pem <中間憑證>` ⇒ `OK`。

## ⛔ 它**不會**讓一張假憑證通過

假的葉憑證仍然要有 `TWCA SSL Certification Authority` 的**簽章**才驗得過，
而那把私鑰不在任何人手上。⇒ 補鏈只補「路」，⛔ 不補「信任」。
"""
import os
import ssl

BUNDLE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                      "certs", "tpex_chain.pem")
_installed = False


def context():
    """→ 一個**系統預設 ＋ 我方補鏈**的 SSLContext。

    ⭐ `create_default_context()` 之後再 `load_verify_locations()` 是**追加**，
      ⛔ 不是取代——系統本來信任的根一張都沒少。
    ⚠ 檔案不在就回**純系統預設**（⛔ 不是回 `CERT_NONE`）：
      補鏈檔遺失應該讓 TPEx 抓不到而**大聲失敗**，
      ⛔ 不可以變成「靜靜地不驗證」。
    """
    ctx = ssl.create_default_context()
    if os.path.exists(BUNDLE):
        ctx.load_verify_locations(cafile=BUNDLE)
    return ctx


def install():
    """把上面那個 context 裝成 `urllib` 的預設 ⇒ **全 repo 的 urlopen 都吃得到**。

    ⭐ 為什麼用這一招而不是逐個呼叫點傳 `context=`：
      本 repo 有 **6 支**各自呼叫 `urlopen`（backfill／fetch／capital／
      mops_history／mops_probe／mops_history_probe）。
      ⛔ 逐個傳 ＝ 同一件事六份，而 CLAUDE.md 四點五 記著這一族已經害過八次
      ——⚠ 而這一次漏掉一支的表現是「那一支的 TPEx 抓取靜靜地繼續失敗」。
    ⚠ 重複呼叫是安全的（`_installed` 擋住）。
    """
    global _installed
    if _installed:
        return False
    ssl._create_default_https_context = context      # noqa: SLF001
    _installed = True
    return True


install()

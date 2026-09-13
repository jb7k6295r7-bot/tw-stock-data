#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TPEx／TWSE 的 TLS 憑證鏈探針。⛔ 只讀不寫資料，也**不改任何驗證設定**。

## 為什麼有這一支（2026-09-13）

`otcsbl` 在 Actions 上第一發就掛：

    URLError: <urlopen error [SSL: CERTIFICATE_VERIFY_FAILED]
              certificate verify failed: unable to get local issuer certificate

⚠ 兩次獨立觀察（2015-05-11、2026-09-11）、兩次都**瞬間**失敗（0 秒）
⇒ ⛔ 不是限流、不是日期下限。而 TWSE 那邊 2,850 天剛剛全部跑完沒事
⇒ **是 TPEx 這一站的憑證鏈**。

## ⛔ 這一支要回答的，是「該怎麼修」，不是「有沒有壞」

`unable to get local issuer certificate` 有兩種完全不同的成因，
⭐ 而**兩種的處置相反**：

    ① 對方少送中間憑證（server 設定漏了）  ⇒ 我方要自己補鏈，或改用會補鏈的取得方式
    ② 我方 CA 太舊（系統 ca-certificates 沒有那個新根） ⇒ 換一份新的 CA（certifi）就好

⇒ 所以這一支**同一個網址打三次**：系統 CA／`certifi` 的 CA／不驗證（只為了把
**對方送了幾張憑證**問出來）。

⛔⛔ 「不驗證」那一發**只用來讀憑證鏈，不讀任何資料**，而且結果只進這份報告。
⚠ 它不是修法，也不可以變成修法——⭐ 判準是：
**若 certifi 那一發就通了，那是我方 CA 太舊；若三發只有不驗證那發通，那是對方少送中間憑證。**
"""
import io
import json
import os
import socket
import ssl
import sys
import urllib.request

HOSTS = [
    ("TPEx（今天掛的那一站）", "www.tpex.org.tw",
     "https://www.tpex.org.tw/www/zh-tw/margin/sbl?date=2026/09/11&id=&response=json"),
    ("TWSE（對照組，剛剛才跑完 2,850 天）", "www.twse.com.tw",
     "https://www.twse.com.tw/rwd/zh/afterTrading/MI_INDEX?date=20260911&type=ALL&response=json"),
    ("TPEx openapi（同一站的另一條）", "www.tpex.org.tw",
     "https://www.tpex.org.tw/openapi/v1/tpex_mainboard_daily_close_quotes"),
]
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                   "data", "meta", "_tls_probe.txt")
UA = {"User-Agent": "Mozilla/5.0 (compatible; tw-stock-data/1.0)"}


def _try(url, ctx, label, lines):
    """打一發，只印**結果**。⛔ 不印回應內容（這支不讀資料）。"""
    req = urllib.request.Request(url, headers=UA)
    try:
        with urllib.request.urlopen(req, timeout=25, context=ctx) as r:
            n = len(r.read())
            lines.append(f"    {label:22} ✅ HTTP {r.status}｜{n:,} bytes")
            return True
    except Exception as ex:                                    # noqa: BLE001
        # ⭐ 完整訊息，⛔ 不砍尾巴——這一族可行動的部分永遠在後面
        lines.append(f"    {label:22} ✗ {type(ex).__name__}: "
                     + " ".join(str(ex).split()))
        return False


def _chain(host, lines):
    """⛔ 只為了**數對方送了幾張憑證**、看它們是誰。不讀任何資料。"""
    raw = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    raw.check_hostname = False
    raw.verify_mode = ssl.CERT_NONE
    try:
        with socket.create_connection((host, 443), timeout=20) as s:
            with raw.wrap_socket(s, server_hostname=host) as ss:
                der = ss.getpeercert(binary_form=True)
                cert = ss.getpeercert()          # CERT_NONE ⇒ 多半是 {}
                try:
                    chain = ss.get_verified_chain()
                except Exception:                              # noqa: BLE001
                    chain = None
    except Exception as ex:                                    # noqa: BLE001
        lines.append(f"    憑證鏈             ✗ 連不上：{type(ex).__name__}: {ex}")
        return
    lines.append(f"    對方送的葉憑證       {len(der):,} bytes")
    if cert:
        lines.append(f"      subject={cert.get('subject')}｜notAfter={cert.get('notAfter')}")
    # ⭐ 這一格才是判準：**對方一共送了幾張**
    if chain is None:
        lines.append("    ⚠ 這個 Python 版本問不到完整鏈（`get_verified_chain` 不在）"
                     "⇒ ⛔ 無法從這裡判斷對方有沒有漏送中間憑證")
    else:
        lines.append(f"    ⭐ 對方一共送了 **{len(chain)} 張**憑證"
                     "（1 張 ⇒ **只有葉憑證、沒有中間憑證** ⇒ 是對方漏送）")


def main():
    lines = [f"tls_probe.py　{__doc__.splitlines()[0]}", "",
             "⛔ 只讀不寫資料，也**不改任何驗證設定**。三發的差別只在「拿哪一份 CA」。", ""]
    try:
        import certifi
        cpath = certifi.where()
        lines.append(f"certifi：**有**（{cpath}）")
    except ImportError:
        certifi, cpath = None, ""
        lines.append("certifi：**無** ⇒ ⚠ 第二發跳過，⛔ 這一趟答不出「是不是我方 CA 太舊」")
    lines.append("")

    verdicts = {}
    for name, host, url in HOSTS:
        lines.append("=" * 68)
        lines.append(f"■ {name}")
        lines.append(f"  {url[:110]}")
        sysctx = ssl.create_default_context()
        ok_sys = _try(url, sysctx, "系統 CA", lines)
        ok_certifi = None
        if cpath:
            ok_certifi = _try(url, ssl.create_default_context(cafile=cpath),
                              "certifi 的 CA", lines)
        _chain(host, lines)
        verdicts[name] = (ok_sys, ok_certifi)
        lines.append("")

    lines.append("=" * 68)
    lines.append("■ 判讀（⛔ 照這三格看，不要自己推）")
    for name, (a, b) in verdicts.items():
        if a:
            v = "✅ 系統 CA 就通了 ⇒ 這一站沒問題"
        elif b:
            v = ("⭐ **系統 CA 不通、certifi 通** ⇒ **我方 CA 太舊**"
                 "⇒ 修法：workflow 裝 certifi 並讓程式用它（⛔ 不是關掉驗證）")
        elif b is False:
            v = ("⛔ **兩份 CA 都不通** ⇒ 多半是**對方漏送中間憑證**"
                 "（看上面「對方一共送了幾張」）⇒ 修法：補中間憑證，"
                 "⛔ **仍然不可以關掉驗證**")
        else:
            v = "⚠ certifi 不在 ⇒ 這一趟判不出來"
        lines.append(f"  {name}：{v}")
    lines.append("")
    lines.append("⛔⛔ 不論結果是哪一格，**都不可以用 `verify=False`／`CERT_NONE` 當修法**。")

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    io.open(OUT, "w", encoding="utf-8").write("\n".join(lines) + "\n")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())

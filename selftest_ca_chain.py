#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""`ca_chain` 的自測：補鏈**有補上**，而且**沒有降低驗證**。

## ⛔ 這一節最重要的一條是反向的

補鏈這種東西，最糟的壞法**不是「沒補到」**（那會抓不到資料，很吵），
⭐ 是**「順手把驗證關掉」**——⚠ 那會安靜地成功，而且成功得跟對的一模一樣。
⇒ 所以這裡有三條在盯 `verify_mode` / `check_hostname` / 沒有 `CERT_NONE`。
"""
import io
import os
import ssl
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import ca_chain                                                # noqa: E402

OK = FAIL = 0


def ck(name, cond, hint=""):
    global OK, FAIL
    if cond:
        OK += 1
        print(f"  ok   {name}")
    else:
        FAIL += 1
        print(f"  ✗    {name}" + (f"｜{hint}" if hint else ""))


def main():
    print("=" * 64)
    print("ca_chain：補鏈有補上，而且沒有降低驗證（不連網）")
    print("=" * 64)

    print("\n── ① 補鏈檔本身 ──")
    ck("⭐ 補鏈檔存在", os.path.exists(ca_chain.BUNDLE), ca_chain.BUNDLE)
    pem = io.open(ca_chain.BUNDLE, encoding="utf-8").read()
    n = pem.count("-----BEGIN CERTIFICATE-----")
    # ⛔ **兩張**，不是一張：中間憑證的發行者是 `TWCA CYBER Root CA`，
    #   而它**不在**系統信任庫裡 ⇒ 還要那張把它接到 `TWCA Global Root CA` 的交叉憑證。
    #   ⚠ 我第一版只放一張，本機一驗就接不上。
    ck("⭐ 裡面是**兩張**（中間憑證＋交叉憑證）⛔ 一張不夠", n == 2, f"⛔ {n} 張")
    subj = subprocess.run(["openssl", "crl2pkcs7", "-nocrl", "-certfile",
                           ca_chain.BUNDLE], capture_output=True)
    txt = subprocess.run(["openssl", "pkcs7", "-print_certs", "-noout"],
                         input=subj.stdout, capture_output=True).stdout.decode()
    ck("⭐ 第一張是 TPEx 漏送的那張中間憑證",
       "CN = TWCA SSL Certification Authority" in txt, txt[:200])
    ck("⭐ 第二張把它接到**系統本來就信任的**根（TWCA Global Root CA）",
       "CN = TWCA CYBER Root CA" in txt and "TWCA Global Root CA" in txt, txt[:300])

    print("\n── ② ⛔ 而它**沒有**降低驗證（這一節是反向的，最重要）──")
    c = ca_chain.context()
    ck("⛔ `verify_mode` 仍然是 CERT_REQUIRED", c.verify_mode == ssl.CERT_REQUIRED,
       str(c.verify_mode))
    ck("⛔ `check_hostname` 仍然是 True", c.check_hostname is True)
    # ⛔ 比 **AST**，不是比字串——`CERT_NONE` 四個字在說明文字裡也有一份
    #   （那一段正是在解釋「為什麼不可以用它」）⇒ 比字串會永遠紅。
    #   ⚠ 而反過來只濾註解也不行：模組說明是 docstring，不是 `#`。
    import ast as _ast
    src = io.open(os.path.join(HERE, "ca_chain.py"), encoding="utf-8").read()
    tree = _ast.parse(src)
    bad = [n for n in _ast.walk(tree)
           if isinstance(n, _ast.Attribute) and n.attr == "CERT_NONE"]
    off = [n for n in _ast.walk(tree)
           if isinstance(n, _ast.Assign)
           and any(getattr(t, "attr", "") == "check_hostname" for t in n.targets)
           and isinstance(n.value, _ast.Constant) and n.value.value is False]
    ck("⛔ 程式碼裡**沒有** `ssl.CERT_NONE`（⚠ 說明文字裡有那四個字是刻意的）",
       not bad, f"⛔ 有 {len(bad)} 處")
    ck("⛔ 程式碼裡**沒有** `check_hostname = False`", not off, f"⛔ 有 {len(off)} 處")

    # ⭐ 而 `install()` 要**真的**把 urllib 的預設換掉——⛔ 沒換的話
    #   六支程式的 `urlopen` 一律走系統預設 ⇒ TPEx 照樣抓不到，
    #   ⚠ 而這一支的其他斷言**全部照樣綠**（突變 M3 實測）。
    ck("⭐ `install()` 真的把 urllib 的預設 SSLContext 換成我方這一份",
       ssl._create_default_https_context is ca_chain.context,      # noqa: SLF001
       f"⛔ 現在是 {ssl._create_default_https_context}")            # noqa: SLF001
    ck("★ 反向驗：那個預設**不是**原廠的 `create_default_context`"
       "（⛔ 一樣的話上面那條是假的）",
       ssl._create_default_https_context is not ssl.create_default_context)  # noqa: SLF001

    print("\n── ③ 它真的**多**了兩張，⛔ 不是把系統那份換掉 ──")
    base = len(ssl.create_default_context().get_ca_certs())
    got = len(c.get_ca_certs())
    ck("⭐ 系統預設的根**一張都沒少**，而且剛好多兩張",
       got == base + 2, f"系統 {base} → 補鏈後 {got}")

    print("\n── ④ 鏈真的接得起來（⛔ 離線驗，不連網）──")
    one = "-----BEGIN CERTIFICATE-----" + pem.split(
        "-----BEGIN CERTIFICATE-----")[1]
    tmp = os.path.join("/tmp", "_cc_leaf.pem")
    io.open(tmp, "w", encoding="utf-8").write(one)
    r = subprocess.run(["openssl", "verify", "-untrusted", ca_chain.BUNDLE, tmp],
                       capture_output=True, text=True)
    ck("⭐ `openssl verify` 用這兩張就走得到系統信任的根", r.returncode == 0,
       (r.stdout + r.stderr).strip()[:200])
    os.remove(tmp)

    print("\n── ⑤ 每一支會 urlopen 的程式都吃得到（⛔ 不是只有 backfill）──")
    for m in ("backfill.py", "fetch.py", "capital.py", "mops_history.py",
              "mops_probe.py", "mops_history_probe.py"):
        s = io.open(os.path.join(HERE, m), encoding="utf-8").read()
        b = "\n".join(l for l in s.split("\n") if not l.lstrip().startswith("#"))
        ck(f"{m} 有 `import ca_chain`", "import ca_chain" in b,
           "⛔ 少了它 ⇒ 這一支的 TPEx 抓取會**靜靜地繼續失敗**")

    print("\n── ⑥ 快到期要先叫（⛔ 不是等它過期那天才發現）──")
    import datetime
    out = subprocess.run(["openssl", "crl2pkcs7", "-nocrl", "-certfile",
                          ca_chain.BUNDLE], capture_output=True)
    dates = subprocess.run(["openssl", "pkcs7", "-print_certs"],
                           input=out.stdout, capture_output=True).stdout
    ends = subprocess.run(["openssl", "x509", "-noout", "-enddate"],
                          input=dates, capture_output=True).stdout.decode()
    # 只取得到第一張的到期日就夠——⭐ 兩張裡先到期的那張才是判準，見下面
    alls = []
    for blk in pem.split("-----END CERTIFICATE-----")[:-1]:
        b = blk[blk.index("-----BEGIN"):] + "-----END CERTIFICATE-----\n"
        d = subprocess.run(["openssl", "x509", "-noout", "-enddate"],
                           input=b.encode(), capture_output=True).stdout.decode()
        alls.append(d.strip().split("=", 1)[1])
    soon = min(datetime.datetime.strptime(x, "%b %d %H:%M:%S %Y %Z")
               for x in alls)
    left = (soon - datetime.datetime.utcnow()).days
    ck(f"⭐ 最早到期的那張還有 **{left} 天**（⛔ 少於 180 天就要換）",
       left > 180, f"⛔ 只剩 {left} 天，{soon}｜{ends.strip()}")

    print(f"\n[selftest] 通過 {OK}｜失敗 {FAIL}")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())

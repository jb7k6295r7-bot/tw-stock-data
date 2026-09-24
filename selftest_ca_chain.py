#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""`ca_chain` 的自測：補鏈**有補上**，而且**沒有降低驗證**。

## ⛔ 這一節最重要的一條是反向的

補鏈這種東西，最糟的壞法**不是「沒補到」**（那會抓不到資料，很吵），
⭐ 是**「順手把驗證關掉」**——⚠ 那會安靜地成功，而且成功得跟對的一模一樣。
⇒ 所以這裡有三條在盯 `verify_mode` / `check_hostname` / 沒有 `CERT_NONE`。
"""
import io
import re
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


def has_dn(txt, field, value):
    """→ txt 裡有沒有這個 DN 欄位／值，⭐ 不看 openssl 的空白排版。

    ⛔ openssl `-print_certs` 對等號兩邊的空白【各版本不同】：
      OpenSSL 3.0 印 `CN = X`　OpenSSL 3.5 印 `CN=X`
    ⇒ 比字面會在「換了一個 openssl」時紅在假原因上。
    ⚠ 而只放寬成 `value in txt` 會變成永遠綠（值也出現在別的欄位與說明文字裡）
      ⇒ ⭐ 所以正規化之後【連欄位名一起比】。
    """
    flat = re.sub(r"[ 	]*=[ 	]*", "=", txt)
    return ("%s=%s" % (field, value)) in flat


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
       has_dn(txt, "CN", "TWCA SSL Certification Authority"), txt[:200])
    ck("⭐ 第二張把它接到**系統本來就信任的**根（TWCA Global Root CA）",
       has_dn(txt, "CN", "TWCA CYBER Root CA")
       and has_dn(txt, "CN", "TWCA Global Root CA"), txt[:300])
    # ★★ 上面兩格用的 has_dn 自己要有樣本，⛔ 否則它可能是一支「永遠回 True」
    ck("★ has_dn 不看排版：`CN = X` 與 `CN=X` 兩種都判得出來",
       has_dn("subject=C=TW, CN = A Root", "CN", "A Root")
       and has_dn("subject=C=TW, CN=A Root", "CN", "A Root"))
    ck("★ has_dn 不在裡面時【必須】判不通過（⛔ 不可以永遠綠）",
       not has_dn("subject=C=TW, CN=B Root", "CN", "A Root"))
    ck("★ has_dn 連【欄位名】一起比（⛔ 值出現在別的欄位不算）",
       not has_dn("subject=C=TW, O=A Root", "CN", "A Root"))

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

    print("\n── ⑤ 每一支會自己開連線的程式都**真的**吃得到 ──")
    # ⛔⛔ 這一節第一版是 grep `import ca_chain`——⚠ 而那是錯的判準：
    #   `ca_chain.install()` 換的是**行程層級**的預設，所以只要**任何一條 import 路徑**
    #   走到它就生效（`feeds` 自己沒有那一行，但它 import `backfill`）。
    #   ⇒ 判準是**行為**：把那支 import 起來，看 urllib 的預設有沒有真的被換掉。
    # ⚠ 而第一版的行為測試**也是假的**：我在檢查之前自己 `import ca_chain`
    #   ⇒ 13 支全 OK。⛔ 那不是它們吃得到，是我親手裝的（2026-09-13 當場踩到）。
    #   ⇒ 改成用 `sys.modules.get("ca_chain")` 問「**它自己**有沒有帶進來」。
    need = ["backfill", "capital", "feeds", "fetch", "mops_history",
            "mops_history_probe", "mops_probe", "suspend", "suspend_probe",
            "tdcc_probe", "twparse", "twsthr_probe"]
    code = ("import importlib, ssl, sys\n"
            "importlib.import_module(sys.argv[1])\n"
            "cc = sys.modules.get('ca_chain')\n"
            "print('OK' if cc and ssl._create_default_https_context is cc.context"
            " else 'NG')\n")
    for m in need:
        r = subprocess.run([sys.executable, "-c", code, m], cwd=HERE,
                           capture_output=True, text=True, timeout=90)
        ck(f"{m}｜import 之後 urllib 的預設**真的**是補鏈版",
           r.stdout.strip().endswith("OK"),
           "⛔ 沒有 ⇒ 這一支的 TPEx 抓取會**靜靜地繼續失敗**"
           f"｜{(r.stdout + r.stderr).strip()[-120:]}")
    # ⭐ 而 `tls_probe` **故意**不吃：它是量現況的那把尺。
    #   ⛔ 補鏈之後它會永遠回「通」⇒ 下次對方再壞掉沒有任何地方會說。
    r = subprocess.run([sys.executable, "-c", code, "tls_probe"], cwd=HERE,
                       capture_output=True, text=True, timeout=90)
    ck("⭐ 而 `tls_probe` **故意不吃**（它是量現況的尺，吃了就永遠回「通」）",
       r.stdout.strip().endswith("NG"), r.stdout.strip()[-80:])

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
    # ⚠ 要留 naive：soon 是 naive ⇒ 帶 tzinfo 相減會 TypeError
    left = (soon - datetime.datetime.now(
        datetime.timezone.utc).replace(tzinfo=None)).days
    ck(f"⭐ 最早到期的那張還有 **{left} 天**（⛔ 少於 180 天就要換）",
       left > 180, f"⛔ 只剩 {left} 天，{soon}｜{ends.strip()}")

    print(f"\n[selftest] 通過 {OK}｜失敗 {FAIL}")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())

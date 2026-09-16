#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""`push_data.sh` 的自測：**真的開一個 git 沙箱跑它**。⛔ 不連外、不碰 repo。

## ⛔ 為什麼要有這一支（2026-09-15）

probe run 101 印了「✓ 已推上 main」，⚠ 而 main 上**只多了 `_last_run.md`**
——那一趟寫出來的 22 份探針輸出**一個都沒有搬過去**。

```
[push_data] 本趟改到 23 個 data 檔
error: pathspec 'data/meta/_ci_steps.tsv' did not match any file(s) known to git
[push_data] ✓ 已推上 main            ← ⛔ 而 22 個檔沒到
```

⭐ 病根：那一步是**一整批** `xargs git checkout "$DC" -- <23 個路徑>`，
而其中一個在本趟被**刪掉**了 ⇒ 整批失敗 ⇒ 另外 22 個一個都沒取出來。
⚠ `xargs` 的失敗沒有人接 ⇒ ⛔ 它照樣往下 commit、push、印成功。

⇒ 這是四點二那一族：**「推成功了」≠「東西搬過去了」**。
⇒ 判準只能是**終點**：搬完之後，main 上那幾個檔要**逐位元組等於本趟的**。
"""
import io
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
OK = FAIL = 0


def ck(name, cond, hint=""):
    global OK, FAIL
    if cond:
        OK += 1
        print(f"  ok   {name}")
    else:
        FAIL += 1
        print(f"  ✗    {name}" + (f"｜{hint}" if hint else ""))


def git(cwd, *a, **kw):
    return subprocess.run(["git"] + list(a), cwd=cwd, capture_output=True,
                          text=True, **kw)


def write(p, s):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    io.open(p, "w", encoding="utf-8").write(s)


def build(d):
    """做一個 origin（bare）＋ 一個工作副本，main 上已經有幾個 data 檔。"""
    origin = os.path.join(d, "origin.git")
    work = os.path.join(d, "work")
    subprocess.run(["git", "init", "-q", "--bare", "-b", "main", origin],
                   check=True)
    subprocess.run(["git", "init", "-q", "-b", "main", work], check=True)
    git(work, "config", "user.email", "t@example.invalid")
    git(work, "config", "user.name", "t")
    git(work, "remote", "add", "origin", origin)
    for n in ("a", "b", "c"):
        write(os.path.join(work, "data", "meta", f"_{n}.txt"), f"main-{n}\n")
    write(os.path.join(work, "data", "meta", "_doomed.txt"), "main-doomed\n")
    write(os.path.join(work, "data", "meta", "_last_run.md"),
          "## x　✓ 正常\n\n最後執行：2026-09-01T00:00:00+08:00（台北）\n\n")
    git(work, "add", "-A")
    git(work, "commit", "-q", "-m", "seed")
    git(work, "push", "-q", "origin", "main")
    # ⭐ 開一個分支，模擬 workflow 的 checkout
    git(work, "checkout", "-q", "-b", "feature")
    return origin, work


def main():
    d = tempfile.mkdtemp(prefix="pushdata_")
    try:
        origin, work = build(d)
        shutil.copy(os.path.join(HERE, "push_data.sh"), work)
        for helper in ("merge_last_run.py", "merge_ledger.py"):
            shutil.copy(os.path.join(HERE, helper), work)

        # ── 本趟：改三個檔、刪一個檔（⭐ 就是 run 101 的形狀）──
        for n in ("a", "b", "c"):
            write(os.path.join(work, "data", "meta", f"_{n}.txt"), f"本趟-{n}\n")
        write(os.path.join(work, "data", "meta", "_last_run.md"),
              "## x　✓ 正常\n\n最後執行：2026-09-15T00:00:00+08:00（台北）\n\n")
        os.remove(os.path.join(work, "data", "meta", "_doomed.txt"))

        r = subprocess.run(["bash", "push_data.sh", "測試"], cwd=work,
                           capture_output=True, text=True,
                           env=dict(os.environ, GITHUB_REF_NAME="feature"))
        out = r.stdout + r.stderr
        print("── ① 改三個檔 ＋ 刪一個檔（⭐ run 101 的形狀）──")
        ck("push_data 回 0", r.returncode == 0, f"rc={r.returncode}｜{out[-400:]}")

        # ⭐⭐ 判準是**終點**：main 上那三個檔要逐位元組等於本趟的
        got = {}
        for n in ("a", "b", "c"):
            g = git(work, "show", f"origin/main:data/meta/_{n}.txt")
            got[n] = g.stdout
        ck("⭐⭐ 三個改過的檔**都**搬到 main 了"
           "（⛔ 這是 run 101 沒做到的那一件：它只搬了 `_last_run.md`）",
           all(got[n] == f"本趟-{n}\n" for n in ("a", "b", "c")), str(got))
        g = git(work, "show", "origin/main:data/meta/_doomed.txt")
        ck("  而被刪掉的那個在 main 上**也刪掉了**", g.returncode != 0, g.stdout[:80])
        lr = git(work, "show", "origin/main:data/meta/_last_run.md").stdout
        ck("  `_last_run.md` 也更新了（逐區塊合併那條路）",
           "2026-09-15" in lr, lr[:120])

        # ── ② 反向驗：取不出來時要**大聲失敗**，⛔ 不可以照樣印成功 ──
        print("\n── ② 反向驗：有檔取不出來 ⇒ ⛔ 不可以照樣 push ──")
        bad = os.path.join(d, "push_bad.sh")
        src = io.open(os.path.join(HERE, "push_data.sh"), encoding="utf-8").read()
        # ⭐ 把 KEEP 裡塞一個不存在的路徑（＝ run 101 那個被刪掉的檔的角色）
        src = src.replace('    [ -n "$hit" ] || KEEP=$(printf \'%s\\n%s\' "$KEEP" "$f")',
                          '    [ -n "$hit" ] || KEEP=$(printf \'%s\\n%s\\n%s\' '
                          '"$KEEP" "$f" "data/meta/_nope.txt")')
        io.open(bad, "w", encoding="utf-8").write(src)
        shutil.copy(bad, os.path.join(work, "push_bad.sh"))
        git(work, "checkout", "-q", "feature")
        write(os.path.join(work, "data", "meta", "_a.txt"), "第二趟\n")
        r2 = subprocess.run(["bash", "push_bad.sh", "測試2"], cwd=work,
                            capture_output=True, text=True,
                            env=dict(os.environ, GITHUB_REF_NAME="feature"))
        o2 = r2.stdout + r2.stderr
        ck("⛔ 有檔取不出來 ⇒ **回非 0**（⚠ 靜靜跳過就是 run 101 的病根）",
           r2.returncode != 0, f"rc={r2.returncode}｜{o2[-300:]}")
        ck("  而且**點名**是哪一個取不出來", "_nope.txt" in o2, o2[-300:])
        # ⚠ 比的是**那一行成功訊息的整串**，⛔ 不是「已推上 main」這幾個字
        #   ——⭐ 失敗訊息裡本來就引用了那句話（跟 `selftest_ca_chain` 盯
        #   `CERT_NONE` 時踩到的同一個：那幾個字在說明文字裡也有一份）。
        ck("⛔⛔ 而且**沒有**印成功那一行（⚠ 它會讓人以為東西到了）",
           "[push_data] ✓ 已推上 main" not in o2, o2[-300:])
        a_now = git(work, "show", "origin/main:data/meta/_a.txt").stdout
        ck("⭐ main 上那個檔**沒有被動到**（⇒ 失敗就是失敗，不是半套）",
           a_now == "本趟-a\n", repr(a_now))
    finally:
        shutil.rmtree(d, ignore_errors=True)

    # ══════════════════════════════════════════════════════════════
    # ③ ⛔⛔ `sync_code.sh`：**push 失敗不可以靜靜 exit 0**
    #
    # ⚠ 它本來寫成 `git push … && echo "✓ 程式已同步到 main"`
    #   ⇒ push 被搶先／被拒絕時，畫面上只是**少了一行成功訊息**，
    #   ⛔ 而腳本回 0 ⇒ 那一步是綠的、main 上的程式一個字都沒更新。
    # ⭐ 而 `probe.yml` 的註解早就寫著該怎麼辦：
    #   「走到 push 還失敗就是**真的有問題**，該紅。」
    # ══════════════════════════════════════════════════════════════
    d3 = tempfile.mkdtemp(prefix="synccode_")
    try:
        print("\n── ③ `sync_code.sh`：push 推不上去 ⇒ ⛔ 不可以回 0 ──")
        origin, work = build(d3)
        shutil.copy(os.path.join(HERE, "sync_code.sh"), work)
        write(os.path.join(work, "hello.py"), "print(1)\n")
        git(work, "add", "-A")
        git(work, "commit", "-q", "-m", "程式")
        # ⭐⭐ 要讓 **fetch 成功、push 失敗**（⛔ 不是把 origin 指到不存在的路徑
        #   ——那會走到「fetch 失敗 ⇒ 跳過同步」那條正當出口，驗不到這一格）。
        #   ⇒ 在 bare repo 放一個一律拒絕的 `pre-receive` hook。
        hook = os.path.join(origin, "hooks", "pre-receive")
        os.makedirs(os.path.dirname(hook), exist_ok=True)
        io.open(hook, "w", encoding="utf-8").write(
            "#!/bin/sh\necho '拒絕（測試用）' >&2\nexit 1\n")
        os.chmod(hook, 0o755)
        r3 = subprocess.run(["bash", "sync_code.sh"], cwd=work,
                            capture_output=True, text=True,
                            env=dict(os.environ, GITHUB_REF_NAME="feature"))
        o3 = r3.stdout + r3.stderr
        # ⛔⛔ 判準是**行為**（rc 與輸出），⚠ 不是「原始碼裡有沒有 `exit 4`」
        #   ——2026-09-15 我今天第三次踩到同一個：那幾個字**在說明註解裡也有一份**
        #   ⇒ 突變 AB1（把 `exit 4` 改成 `exit 0`）當場全綠。
        ck("⭐⭐ 三次都推不上去 ⇒ **回非 0**"
           "（⚠ 回 0 ＝ 那一步是綠的，而 main 上的程式沒更新）",
           r3.returncode != 0, f"rc={r3.returncode}｜{o3[-400:]}")
        ck("  而且**出聲**（⚠ 少一行成功訊息 ≠ 說出問題）",
           "推不上去" in o3 or "push 失敗" in o3, o3[-400:])
        ck("  而且講出**後果**：排程跑的是 main 上那一份",
           "排程跑的是 main" in o3, o3[-400:])
        ck("⭐ 而且**沒有**印成功那一行",
           "✓ 程式已同步到 main" not in o3, o3[-300:])
    finally:
        shutil.rmtree(d3, ignore_errors=True)

    # ══════════════════════════════════════════════════════════════
    # ④ ⛔⛔ **push 回 0，而東西沒到 main**（K線分析線 2026-09-15〈七十二〉）
    #
    # ⭐ 那條條文的判別法就是這一節要造的情境：
    #   「把那個步驟的實際動作註解掉，成功訊息還會不會印？」
    #   ⇒ 原本的 `git push … && echo "✓ 已推上 main"` 證明的是
    #     **「push 這個命令回了 0」**，⛔ 不是「那些檔到了 main」。
    #   ⚠ 而 2026-09-15 probe run 101 正是這個形狀：push 真的成功了，
    #     ⛔ 只是那個 commit 裡根本沒有那 22 個檔。
    #
    # ⇒ ⭐ 造法：在 bare repo 放 **`post-receive`**（⛔ 不是 `pre-receive`）——
    #   它在 ref 已經更新**之後**才跑 ⇒ push 端看到的是**成功**，
    #   而它把 main 倒回去 ⇒ ⭐ 「推成功了」與「東西在 main 上」當場分家。
    #   ⛔ `pre-receive` 造不出這一格：那會讓 push 失敗（③ 用的是那個）。
    # ══════════════════════════════════════════════════════════════
    d4 = tempfile.mkdtemp(prefix="pushback_")
    try:
        print("\n── ④ push 回 0 而東西沒到 main ⇒ ⛔ 不可以印成功 ──")
        origin, work = build(d4)
        shutil.copy(os.path.join(HERE, "push_data.sh"), work)
        for helper in ("merge_last_run.py", "merge_ledger.py"):
            shutil.copy(os.path.join(HERE, helper), work)
        base = git(work, "rev-parse", "origin/main").stdout.strip()
        hook = os.path.join(origin, "hooks", "post-receive")
        os.makedirs(os.path.dirname(hook), exist_ok=True)
        io.open(hook, "w", encoding="utf-8").write(
            f"#!/bin/sh\ngit update-ref refs/heads/main {base}\n")
        os.chmod(hook, 0o755)
        write(os.path.join(work, "data", "meta", "_a.txt"), "第四趟\n")
        r4 = subprocess.run(["bash", "push_data.sh", "測試4"], cwd=work,
                            capture_output=True, text=True,
                            env=dict(os.environ, GITHUB_REF_NAME="feature"))
        o4 = r4.stdout + r4.stderr
        ck("⭐⭐ push 回 0 而 main 上沒有那個檔 ⇒ **回非 0**"
           "（⚠ 這是 run 101 那一趟印「✓ 已推上 main」的那一格）",
           r4.returncode != 0, f"rc={r4.returncode}｜{o4[-500:]}")
        ck("  而且**點名**是哪一個檔對不上",
           "_a.txt" in o4, o4[-500:])
        # ⚠ 比的是那一行成功訊息的**整串**（第七點⑧：那幾個字在說明文字裡也有一份）
        ck("⛔⛔ 而且**沒有**印成功那一行",
           "[push_data] ✓ 已推上 main" not in o4, o4[-500:])
        ck("⭐ 而且講得出**為什麼**：我的 commit 不在 main 的歷史裡",
           "不在 main 的歷史裡" in o4, o4[-500:])
        # ⭐ 而正向那一半也要有：①那一趟的成功訊息要說出它**讀回來比過**，
        #   ⛔ 否則「有沒有做讀回驗證」跟「做了」長得一模一樣。
        ck("⭐ 而正常那一趟（①）的成功訊息說得出它是**讀回來比過**的",
           "讀回來逐檔比過" in out, out[-300:])
    finally:
        shutil.rmtree(d4, ignore_errors=True)

    # ══════════════════════════════════════════════════════════════
    # ⑤ ⛔⛔ `sync_code.sh`：**分支上刪掉的檔，main 上也要刪掉**
    #
    # ⚠ 2026-09-16 付過代價：`site_recon.py` 2026-09-13 在分支上刪了，
    #   ⛔ 而 main 上那一份一直在 ⇒ probe run 126 的 `selftest_probes.py`
    #   在 main 上 rc=1（母體 21 支、沒叫 `probe_stamp()` 的就是它），
    #   ⭐ 而同一支自測在分支上是**綠的**——同一支程式、同一天、兩個答案。
    #
    # ⇒ ⭐ 判準是**終點**：同步完之後，去 origin/main 上**看那個檔還在不在**。
    #   ⛔ 不是「sync_code 有沒有印刪除那一行」（第七點⑧：比行為，不比字串）。
    # ══════════════════════════════════════════════════════════════
    d5 = tempfile.mkdtemp(prefix="syncdel_")
    try:
        print("\n── ⑤ `sync_code.sh`：分支刪掉的檔 ⇒ main 上也要刪掉 ──")
        origin, work = build(d5)
        shutil.copy(os.path.join(HERE, "sync_code.sh"), work)
        write(os.path.join(work, "hello.py"), "print(1)\n")
        write(os.path.join(work, "gone.py"), "print(2)\n")
        git(work, "add", "-A")
        git(work, "commit", "-q", "-m", "程式")
        env5 = dict(os.environ, GITHUB_REF_NAME="feature")
        r = subprocess.run(["bash", "sync_code.sh"], cwd=work,
                           capture_output=True, text=True, env=env5)
        ck("  前置：第一趟同步把兩支程式推上 main",
           r.returncode == 0
           and git(work, "show", "origin/main:gone.py").returncode == 0,
           (r.stdout + r.stderr)[-300:])

        # ── 本趟：刪掉 gone.py、改 hello.py，⭐ 並且**也刪掉一個 data 檔** ──
        #   （後者是閘門①的正例：`data/` 是排除樹，⛔ 一個都不准刪）
        os.remove(os.path.join(work, "gone.py"))
        os.remove(os.path.join(work, "data", "meta", "_a.txt"))
        write(os.path.join(work, "hello.py"), "print(99)\n")
        git(work, "add", "-A")
        git(work, "commit", "-q", "-m", "刪掉 gone.py")
        r5 = subprocess.run(["bash", "sync_code.sh"], cwd=work,
                            capture_output=True, text=True, env=env5)
        o5 = r5.stdout + r5.stderr
        ck("sync_code 回 0", r5.returncode == 0, f"rc={r5.returncode}｜{o5[-400:]}")
        g = git(work, "show", "origin/main:gone.py")
        ck("⭐⭐ 分支刪掉的 `gone.py` 在 **main 上也不見了**"
           "（⛔ 這是 `site_recon.py` 沒做到的那一件）",
           g.returncode != 0, g.stdout[:80])
        ck("  而改過的 `hello.py` 照樣搬過去",
           git(work, "show", "origin/main:hello.py").stdout == "print(99)\n",
           git(work, "show", "origin/main:hello.py").stdout[:80])
        # ⛔⛔ 閘門①：`data/` 是排除樹 ⇒ 分支刪了也**不准**跟著刪
        a = git(work, "show", "origin/main:data/meta/_a.txt")
        ck("⛔⛔ 而分支刪掉的 **`data/` 檔在 main 上還在**"
           "（⚠ 排除樹的主詞是『誰寫它』——資料是 main 寫的）",
           a.returncode == 0 and a.stdout == "main-a\n", repr(a.stdout[:80]))
    finally:
        shutil.rmtree(d5, ignore_errors=True)

    # ══════════════════════════════════════════════════════════════
    # ⑥ ⭐⭐ 閘門②：一趟要刪太多 ⇒ **一個都不刪**，而且**不算失敗**
    #
    # ⛔ 刪除是這支唯一會毀掉東西的動作 ⇒ 失控地刪是最糟的結果。
    # ⚠ 而處置不是「整趟紅」：紅掉 ＝ 程式沒同步到 main ⇒ 排程跑舊程式。
    # ⇒ ⭐ 六點五那條：**跳掉的那一層要大聲出聲**，新增／覆蓋照常。
    # ══════════════════════════════════════════════════════════════
    d6 = tempfile.mkdtemp(prefix="synccap_")
    try:
        print("\n── ⑥ 一趟要刪 25 個 ⇒ 一個都不刪，⛔ 而且不算失敗 ──")
        origin, work = build(d6)
        shutil.copy(os.path.join(HERE, "sync_code.sh"), work)
        many = [f"m{i:02d}.py" for i in range(25)]
        for n in many:
            write(os.path.join(work, n), "print(0)\n")
        write(os.path.join(work, "keep.py"), "print(1)\n")
        git(work, "add", "-A")
        git(work, "commit", "-q", "-m", "一堆程式")
        env6 = dict(os.environ, GITHUB_REF_NAME="feature")
        subprocess.run(["bash", "sync_code.sh"], cwd=work,
                       capture_output=True, text=True, env=env6)
        for n in many:
            os.remove(os.path.join(work, n))
        write(os.path.join(work, "keep.py"), "print(2)\n")
        git(work, "add", "-A")
        git(work, "commit", "-q", "-m", "一次刪 25 個")
        r6 = subprocess.run(["bash", "sync_code.sh"], cwd=work,
                            capture_output=True, text=True, env=env6)
        o6 = r6.stdout + r6.stderr
        ck("⭐ 超過上限 ⇒ **不算失敗**（⛔ 紅掉 ＝ 程式沒同步 ⇒ 排程跑舊的）",
           r6.returncode == 0, f"rc={r6.returncode}｜{o6[-400:]}")
        alive = sum(1 for n in many
                    if git(work, "show", f"origin/main:{n}").returncode == 0)
        ck("⭐⭐ 25 個**一個都沒刪**（⛔ 不是刪到上限為止——那是半套）",
           alive == 25, f"main 上還剩 {alive}／25")
        ck("  而且**大聲說出這一層沒跑**（⚠ 一行 skipped 跟一行 ok 長得一樣）",
           "這一層沒跑" in o6, o6[-400:])
        ck("⭐ 而新增／覆蓋照常搬（⇒ 跳掉的只有刪除那一層）",
           git(work, "show", "origin/main:keep.py").stdout == "print(2)\n",
           git(work, "show", "origin/main:keep.py").stdout[:60])
    finally:
        shutil.rmtree(d6, ignore_errors=True)

    # ══════════════════════════════════════════════════════════════
    # ⑦ ⭐⭐ 閘門①**自己**要驗得到：⚠ 它在正常路徑上**走不到**
    #
    # ⛔ ⑤ 那一節的「`data/` 檔還在」其實是 `$SPEC`（`:(exclude)data`）
    #   擋下來的——⭐ 拿掉「排除樹底下一個都不刪」那道閘門，⑤ **照樣全綠**
    #   （實測突變 D2：⛔ 全綠）⇒ 那道閘門**從來沒有被走過**
    #   ⇒ 第七點：**沒證明過會失敗的測試，不算測試**。
    #
    # ⇒ ⭐ 造法跟 ② 一樣：改一份副本，把 DEL 那一行的 `$SPEC` 拔掉
    #   （＝「下一個人把排除清單漏掉」那個未來），⛔ 然後斷言 `data/` **仍然**沒事。
    #   ⚠ 一道閘門的價值就在「上一層漏掉的時候它還在」——
    #     上一層沒漏時它跟不存在**長得一模一樣**。
    # ══════════════════════════════════════════════════════════════
    d7 = tempfile.mkdtemp(prefix="syncguard_")
    try:
        print("\n── ⑦ 拔掉 `$SPEC`（＝上一層漏掉）⇒ ⛔ `data/` 仍然一個都不准刪 ──")
        origin, work = build(d7)
        src = io.open(os.path.join(HERE, "sync_code.sh"), encoding="utf-8").read()
        holed = src.replace('origin/main "$SRC" -- . $SPEC)',
                            'origin/main "$SRC" -- .)')
        ck("  前置：錨點真的換掉了（⛔ 沒換掉 ＝ 這一節什麼都沒驗）",
           holed != src, "錨點抄錯了")
        write(os.path.join(work, "sync_holed.sh"), holed)
        write(os.path.join(work, "hello.py"), "print(1)\n")
        git(work, "add", "-A")
        git(work, "commit", "-q", "-m", "程式")
        env7 = dict(os.environ, GITHUB_REF_NAME="feature")
        subprocess.run(["bash", "sync_holed.sh"], cwd=work,
                       capture_output=True, text=True, env=env7)
        os.remove(os.path.join(work, "data", "meta", "_b.txt"))
        git(work, "add", "-A")
        git(work, "commit", "-q", "-m", "刪掉一個 data 檔")
        r7 = subprocess.run(["bash", "sync_holed.sh"], cwd=work,
                            capture_output=True, text=True, env=env7)
        o7 = r7.stdout + r7.stderr
        b = git(work, "show", "origin/main:data/meta/_b.txt")
        ck("⭐⭐ `$SPEC` 漏掉時，那道閘門**接住了**：`data/` 檔在 main 上還在",
           b.returncode == 0 and b.stdout == "main-b\n", repr(b.stdout[:80]))
        ck("  而且**出聲**點名是哪一條路徑",
           "data/meta/_b.txt" in o7, o7[-400:])
        ck("  而且不算失敗（⛔ 紅掉 ＝ 程式沒同步）", r7.returncode == 0,
           f"rc={r7.returncode}｜{o7[-300:]}")
    finally:
        shutil.rmtree(d7, ignore_errors=True)

    # ══════════════════════════════════════════════════════════════
    # ⑧ ⛔⛔ 刪除清單裡有**一個壞元素** ⇒ 不可以照樣往下 commit／push
    #
    # ⭐ 這是四點二⑥那一條套在刪除上：`push_data.sh` 的
    #   `xargs git checkout … <23 個路徑>` 有一個路徑取不出來
    #   ⇒ **整批失敗** ⇒ 另外 22 個一個都沒搬，⚠ 而它照樣印「✓ 已推上 main」。
    # ⇒ 這裡是**逐一**刪（⇒ 一個壞的毒不死整批），⛔ 而「毒不死整批」還不夠：
    #   一個刪不掉就代表這一趟的刪除**是半套的** ⇒ ⭐ 一定要停在 push 之前。
    #
    # ⚠ 造法：改一份副本，在 DEL 後面塞一個**不存在的路徑**
    #   （＝ run 101 那個「被刪掉的檔」的角色）。
    # ══════════════════════════════════════════════════════════════
    d8 = tempfile.mkdtemp(prefix="syncbad_")
    try:
        print("\n── ⑧ 刪除清單裡有一個壞元素 ⇒ ⛔ 停在 push 之前 ──")
        origin, work = build(d8)
        src = io.open(os.path.join(HERE, "sync_code.sh"), encoding="utf-8").read()
        holed = src.replace(
            'origin/main "$SRC" -- . $SPEC)',
            'origin/main "$SRC" -- . $SPEC; echo nope.py)')
        ck("  前置：錨點真的換掉了", holed != src, "錨點抄錯了")
        write(os.path.join(work, "sync_bad.sh"), holed)
        write(os.path.join(work, "hello.py"), "print(1)\n")
        write(os.path.join(work, "gone.py"), "print(2)\n")
        git(work, "add", "-A")
        git(work, "commit", "-q", "-m", "程式")
        env8 = dict(os.environ, GITHUB_REF_NAME="feature")
        # ⚠ 前置那一趟要用**原版**：改過的那份每一趟都會塞 `nope.py`
        #   ⇒ 連前置都會 exit 5 ⇒ main 上根本沒有 hello.py 可以比
        #   （⛔ 第四個陷阱的變形：情境沒造出來，跟斷言沒用長得一樣）
        shutil.copy(os.path.join(HERE, "sync_code.sh"), work)
        subprocess.run(["bash", "sync_code.sh"], cwd=work,
                       capture_output=True, text=True, env=env8)
        os.remove(os.path.join(work, "gone.py"))
        write(os.path.join(work, "hello.py"), "print(77)\n")
        git(work, "add", "-A")
        git(work, "commit", "-q", "-m", "刪掉 gone.py")
        r8 = subprocess.run(["bash", "sync_bad.sh"], cwd=work,
                            capture_output=True, text=True, env=env8)
        o8 = r8.stdout + r8.stderr
        ck("⭐⭐ 有一個刪不掉 ⇒ **回非 0**（⚠ 靜靜往下走 ＝ 半套的同步）",
           r8.returncode != 0, f"rc={r8.returncode}｜{o8[-400:]}")
        ck("  而且**點名**是哪一個刪不掉", "nope.py" in o8, o8[-400:])
        h = git(work, "show", "origin/main:hello.py").stdout
        ck("⭐ 而 main **沒有被推成半套**（⇒ 停在 push 之前）",
           h == "print(1)\n", repr(h[:60]))
        ck("⭐ 而且**沒有**印成功那一行",
           "✓ 程式已同步到 main" not in o8, o8[-300:])
    finally:
        shutil.rmtree(d8, ignore_errors=True)

    print(f"\n[selftest] 通過 {OK}｜失敗 {FAIL}")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())

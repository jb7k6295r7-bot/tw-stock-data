#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""selftest_probe_step.py — `probe_step.sh` 的自測。

## ⛔ 它守的是兩個**安靜**的壞法（2026-09-16 probe run 131 各付過一次）

```
① 探針炸掉 ⇒ 舊寫法 `git checkout -- <檔>` 還原的是**分支**那一份
   ⇒ 分支的 data/ 永遠比 main 舊 ⇒ 把 main 上的 `_keys_probe.txt` 砍掉 533 行，
   ⚠ 而附加那句「這一份是上一次成功的內容」讓它看起來完全正常
② 探針撞到 step 的 `timeout-minutes` ⇒ **整個 shell 被砍**
   ⇒ 寫 ✗ 那段一行都沒跑 ⇒ 輸出停在上一趟，
   ⚠ 而 `continue-on-error: true` 讓那一步顯示 **success**
```

⇒ ⭐ 這一支**不比原始碼字串**（第七點第八個：那幾個字在上面的說明裡就有一份），
一律**真的跑一次** `probe_step.sh`，比**行為**（rc、輸出檔內容、還原到哪一版）。
"""
import io
import os
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from selftest_workflows import run_blocks as _run_blocks   # noqa: E402  ⭐ 只有一份實作（四點五）

HERE = os.path.dirname(os.path.abspath(__file__))
SH = os.path.join(HERE, "probe_step.sh")
OK = FAIL = 0


def ck(name, cond, hint=""):
    global OK, FAIL
    if cond:
        OK += 1
        print(f"  ok   {name}")
    else:
        FAIL += 1
        print(f"  ✗    {name}｜{hint}")


def _git(cwd, *a):
    return subprocess.run(["git", *a], cwd=cwd, capture_output=True, text=True)


def sandbox():
    """一個有 `origin/main`（新）與分支 HEAD（**舊**）的沙箱 ⇒ 兩者分得出來。"""
    d = tempfile.mkdtemp(prefix="probestep_")
    bare = os.path.join(d, "origin.git")
    work = os.path.join(d, "work")
    subprocess.run(["git", "init", "-q", "--bare", "-b", "main", bare], check=True)
    subprocess.run(["git", "clone", "-q", bare, work], check=True)
    _git(work, "config", "user.email", "t@t"); _git(work, "config", "user.name", "t")
    os.makedirs(os.path.join(work, "data", "meta"))
    f = os.path.join(work, "data", "meta", "_x_probe.txt")
    io.open(f, "w", encoding="utf-8").write("舊：分支這一份\n")
    _git(work, "add", "-A"); _git(work, "commit", "-qm", "b")
    _git(work, "push", "-q", "origin", "HEAD:main")
    # main 往前走一版（＝真實情況：資料是 workflow 推到 main 的）
    io.open(f, "w", encoding="utf-8").write("新：main 那一份\n" * 50)
    _git(work, "add", "-A"); _git(work, "commit", "-qm", "m")
    _git(work, "push", "-q", "origin", "HEAD:main")
    # 分支 HEAD 退回舊的那一版 ⇒ 工作區是舊的，origin/main 是新的
    _git(work, "reset", "-q", "--hard", "HEAD~1")
    _git(work, "fetch", "-q", "origin", "main")
    _git(work, "update-ref", "refs/remotes/origin/main", "FETCH_HEAD")
    return d, work, "data/meta/_x_probe.txt"


def run(work, rel, budget, *cmd):
    p = subprocess.run(["bash", SH, rel, str(budget), *cmd],
                       cwd=work, capture_output=True, text=True)
    body = io.open(os.path.join(work, rel), encoding="utf-8").read()
    return p, body


def main():
    ck("⛔ `probe_step.sh` 存在", os.path.exists(SH))

    # ── ① 成功 ⇒ ⛔ 不可以動輸出檔 ──
    d, work, rel = sandbox()
    try:
        p, body = run(work, rel, 30, "python3", "-c",
                      "open('data/meta/_x_probe.txt','w').write('這一趟的新內容\\n')")
        ck("① 成功 ⇒ rc=0", p.returncode == 0, p.stderr[:200])
        ck("① 成功 ⇒ 輸出檔就是**這一趟**寫的（⛔ 不還原、⛔ 不加 ✗）",
           body.strip() == "這一趟的新內容" and "✗" not in body, repr(body[:200]))
    finally:
        shutil.rmtree(d, ignore_errors=True)

    # ── ② 炸掉 ⇒ ⭐⭐ 要還原成 **origin/main** 那一版，⛔ 不是分支那一版 ──
    d, work, rel = sandbox()
    try:
        # ⛔ 指令字串本身會被 echo 進輸出檔（`$*`）⇒ 哨兵字不可以出現在指令裡，
        #   ⚠ 否則「殘骸留下來了」與「指令被印出來了」分不開（第七點第四個的變形）。
        io.open(os.path.join(work, "boom.py"), "w", encoding="utf-8").write(
            "import io\nio.open('data/meta/_x_probe.txt','w',encoding='utf-8')"
            ".write('CRASHLEFTOVER\\n')\nraise SystemExit(1)\n")
        p, body = run(work, rel, 30, "python3", "boom.py")
        ck("② 炸掉 ⇒ 仍然 rc=0（可見性由資料承擔，⛔ 不賠掉整趟）",
           p.returncode == 0, p.stderr[:200])
        ck("②⭐⭐ 還原的是 **origin/main** 那一版（⛔ 不是分支那份舊的）",
           "新：main 那一份" in body and "舊：分支這一份" not in body,
           repr(body[:200]))
        ck("② ⛔ 這一趟的殘骸沒有留下",
           "CRASHLEFTOVER" not in body, repr(body[:200]))
        ck("② ⭐ 檔案裡講得出它是從哪裡還原的",
           "origin/main" in body, repr(body[-300:]))
        ck("② 有 ✗ 那一行", "✗" in body, repr(body[-300:]))
    finally:
        shutil.rmtree(d, ignore_errors=True)

    # ── ③ ⭐⭐ 撞到時間預算 ⇒ 要**講出它是被砍的**，⛔ 不是「跑完沒發現」 ──
    d, work, rel = sandbox()
    try:
        p, body = run(work, rel, 1, "python3", "-c",
                      "import time; time.sleep(30)")
        ck("③ 撞預算 ⇒ rc=0", p.returncode == 0, p.stderr[:200])
        ck("③⭐⭐ 輸出檔明講**被時間預算砍掉**"
           "（⛔ 「被砍」與「跑完沒發現」在畫面上一模一樣）",
           "時間預算" in body, repr(body[-300:]))
        ck("③ 而且還是還原成 main 那一版",
           "新：main 那一份" in body, repr(body[:200]))
    finally:
        shutil.rmtree(d, ignore_errors=True)

    # ── ④ ⛔ main 上沒有那個檔 ⇒ 要**說它是從本地 HEAD 還原的**，⛔ 不可以假裝 ──
    d, work, rel = sandbox()
    try:
        new = "data/meta/_y_probe.txt"
        io.open(os.path.join(work, new), "w", encoding="utf-8").write("只有分支有\n")
        _git(work, "add", "-A"); _git(work, "commit", "-qm", "y")
        p, body = run(work, new, 30, "python3", "-c", "raise SystemExit(3)")
        ck("④ main 上沒有 ⇒ 明講是從**本地 HEAD** 還原（⛔ 不假裝還原自 main）",
           "本地 HEAD" in body and "origin/main" not in body, repr(body[-300:]))
    finally:
        shutil.rmtree(d, ignore_errors=True)

    # ── ⑤ ⛔ 兩個都還原不了 ⇒ 要**說這一份可能是殘骸**，⛔ 不可以寫「上一次成功的內容」 ──
    d, work, rel = sandbox()
    try:
        untracked = "data/meta/_z_probe.txt"
        io.open(os.path.join(work, untracked), "w", encoding="utf-8").write("殘骸\n")
        p, body = run(work, untracked, 30, "python3", "-c", "raise SystemExit(5)")
        ck("⑤ ⛔ 還原不了 ⇒ 明講「可能是殘骸」"
           "（⛔ 那句『上一次成功的內容』在這裡是**假的**）",
           "殘骸" in body and "還原不了" in body, repr(body[-300:]))
    finally:
        shutil.rmtree(d, ignore_errors=True)

    # ── ⑥ ⭐ 每一支用它的 workflow 步驟，`timeout-minutes` 都要**大於**這裡的秒數 ──
    #    ⛔ 否則外層先砍 ⇒ 這一層等於沒有（那正是 run 131 的病根）
    import re
    wf = io.open(os.path.join(HERE, ".github", "workflows", "probe.yml"),
                 encoding="utf-8").read()
    bad = []
    n = 0
    # ⚠ 這個上限**是母體的一部分**：第一版寫 1200 字 ⇒ 迴圈那一步的
    #   `probe_step.sh` 距離它的 `timeout-minutes:` 太遠 ⇒ **掃不到**
    #   ⇒ 報「掃到 2 處」而實際是 3 處（第七點第九個：母體被判準悄悄縮小）。
    #   ⇒ ⭐ 所以底下 ⑥ 的門檻要釘**母體大小**，⛔ 不是只釘「沒有壞的」。
    for m in re.finditer(r"timeout-minutes:\s*(\d+)([\s\S]*?)(?=\n      - name:|\Z)", wf):
        mins = int(m.group(1))
        for b in re.finditer(r"probe_step\.sh\s+\S+\s+(\d+)", m.group(2)):
            n += 1
            if int(b.group(1)) >= mins * 60:
                bad.append((mins, int(b.group(1))))
    ck(f"⑥ ⭐ 內層秒數 < 外層 `timeout-minutes`（掃到 {n} 處）",
       n >= 3 and not bad,
       f"⛔ 外層比內層小：{bad}" if bad else f"⛔ 母體只有 {n} 處（該有 3 處）")

    # ── ⑦⑧ ⭐⭐ 迴圈自己的 wall-clock 預算（run 133 的病根）──
    #    run 133：那一步跑了 15 分 12 秒撞到 `timeout-minutes: 15`
    #    ⇒ `keys_probe` 以後那幾支**一支都沒跑到**，
    #    ⚠ 而 step 是 **success**、輸出檔逐位元沒變、沒有任何 ✗
    #    ⇒ ⛔ 「沒跑到」與「跑了而且結果沒變」長得一模一樣。
    import re as _re2
    wf_txt = io.open(os.path.join(HERE, ".github", "workflows", "probe.yml"),
                     encoding="utf-8").read()
    # ⛔⛔ 第一版我寫成 `timeout-minutes:(\d+)[\s\S]*?PROBE_LOOP_BUDGET_SEC`
    #   ⇒ 非貪婪是從**檔案裡第一個** `timeout-minutes:` 開始配
    #   ⇒ 抓到的是 **job 層級的 60 分**，⛔ 不是那一步的
    #   ⇒ 把預算改成 2000 秒的突變 **全綠**（2000 < 60×60）。
    #   ⇒ ⭐ 改成：先找到預算那一行，再往**前**找**最近的**一個 `timeout-minutes:`。
    mb = _re2.search(r"PROBE_LOOP_BUDGET_SEC=\$\{PROBE_LOOP_BUDGET_SEC:-(\d+)\}", wf_txt)
    prev = list(_re2.finditer(r"timeout-minutes:\s*(\d+)",
                              wf_txt[:mb.start()])) if mb else []
    ck("⑦ ⭐⭐ 迴圈的 wall-clock 預算 **小於那一步**的 `timeout-minutes`"
       "（⛔ 大於等於的話，步驟先被砍 ⇒ 這一層等於沒有）",
       bool(mb) and bool(prev) and int(mb.group(1)) < int(prev[-1].group(1)) * 60,
       ("找不到預算那一行" if not mb else
        f"預算 {mb.group(1)} 秒 vs **最近的**步驟上限 {prev[-1].group(1)} 分"))

    # ⑧ ⭐ **真的跑一次**那段迴圈（預算設 0 ⇒ 一支都不該跑），
    #    斷言每一支的輸出檔都留下「這一趟沒有跑到」——⛔ 不是比原始碼有沒有那幾個字。
    blocks = [b for _n, b in _run_blocks(os.path.join(HERE, ".github", "workflows",
                                                      "probe.yml"))
              if "PROBE_LOOP_BUDGET_SEC" in b and "LOOP_DEADLINE" in b]
    if not blocks:
        ck("⑧ ⭐ 找得到那段迴圈", False, "probe.yml 裡掃不到 PROBE_LOOP_BUDGET_SEC 的 run 區塊")
    else:
        d = tempfile.mkdtemp(prefix="probeloop_")
        try:
            os.makedirs(os.path.join(d, "data", "meta"))
            names = _re2.findall(r'"([a-z0-9_]+\.py):(_[a-z0-9_]+\.txt)"', blocks[0])
            for _sc, _out in names:
                io.open(os.path.join(d, "data", "meta", _out), "w",
                        encoding="utf-8").write("舊內容\n")
            body = _re2.sub(r"\$\{\{[^}]*\}\}", "workflow_dispatch", blocks[0])
            sh = os.path.join(d, "loop.sh")
            io.open(sh, "w", encoding="utf-8").write(body)
            env = dict(os.environ, PROBE_LOOP_BUDGET_SEC="0")
            p2 = subprocess.run(["bash", sh], cwd=d, capture_output=True,
                                text=True, env=env, timeout=120)
            miss = [o for _s2, o in names
                    if "這一趟沒有跑到" not in
                    io.open(os.path.join(d, "data", "meta", o), encoding="utf-8").read()]
            ck(f"⑧ ⭐⭐ 預算 0 ⇒ **{len(names)} 支全部**在自己的輸出檔留下「沒有跑到」"
               "（⛔ 安靜跳過就是 run 133 那個 bug）",
               bool(names) and not miss, f"沒留下的：{miss[:5]}｜stderr {p2.stderr[:200]}")
            ck("⑧ ⭐ 而且母體是 18 支（⛔ 掃不到就是那條正規式縮小了母體）",
               len(names) >= 18, f"只掃到 {len(names)} 支")
        finally:
            shutil.rmtree(d, ignore_errors=True)

    # ── ⑨ ⭐⭐ hook 有沒有跑「跨檔效應」那一族 ──
    #    2026-09-16 實測到的坑：我在 `selftest_probes.py` 寫了一行 os.remove，
    #    ⇒ `selftest_probes.py` 全綠、⛔ `selftest_no_data_delete.py` 紅
    #    ⇒ hook 一聲都沒吭 ⇒ probe run 134 的 step 6 failure ⇒ 同步整個被 skip。
    #    ⭐ 判準比**行為**：真的跑一次 hook（造一個會讓那道守門紅的暫存檔），
    #    ⛔ 不是比 hook 的原始碼有沒有那幾個字（第七點第八個）。
    hookp = os.path.join(HERE, ".githooks", "pre-commit")
    htxt = io.open(hookp, encoding="utf-8").read() if os.path.exists(hookp) else ""
    ck("⑨ ⭐ hook 有跑跨檔守門 `selftest_no_data_delete.py`"
       "（⛔ 第三道只跑「對應的那一支」，看不到跨檔效應）",
       "selftest_no_data_delete.py" in htxt, "hook 裡找不到")
    ck("⑨ ⭐ 也跑 `selftest_lowwater.py`（同一族）",
       "selftest_lowwater.py" in htxt, "hook 裡找不到")
    ck("⑨ ⛔ 而 `selftest_zero_dep.py` **不收進 hook**（實測 63 秒）"
       "　⚠ 一支慢到讓人想 `--no-verify` 的 hook 等於沒有",
       "selftest_zero_dep" not in htxt.split("for G in")[-1].split("done")[0]
       if "for G in" in htxt else False, "它被收進那個迴圈了")

    print(f"\n[selftest] 通過 {OK}｜失敗 {FAIL}")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())

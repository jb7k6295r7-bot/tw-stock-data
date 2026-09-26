#!/usr/bin/env bash
# push_data.sh — 把「本趟改到的 data 路徑」搬到 main 的頭上，然後推。
#
# 用法：  bash push_data.sh "<commit 訊息>"
# 回傳：  0 = 推上去了（或本來就沒有差異）；非 0 = 真的失敗
#
# ⛔⛔ 為什麼要有這個檔：這段邏輯本來在**八支 workflow 各抄一份**。
#   而「同一段邏輯抄兩份」今晚已經害過一次——`limit` 那個 bug 在
#   `fetch.py` 與 `backfill.py` 各有一份，修好的那份天天跑、
#   沒修的那份只有回補才跑，所以一直沒被發現。
#   ⇒ 這裡只留一份，八支都呼叫它。
#
# ⭐ 做法（2026-09-10，付了 5 小時學費換來的）：
#   ① 程式 commit **一個都不重放** ⇒ workflow／程式檔永遠不會衝突
#   ② `data/` 裡只碰**本趟真的改到的檔** ⇒ 別的 workflow 剛寫的資料原封不動
#   ③ 完全沒有 rebase ⇒ 沒有「衝突要挑哪一邊」的問題
#   離線 git 模擬三項都驗過（scratchpad/gitsim3）。
set -u
MSG="${1:?用法: push_data.sh \"<commit 訊息>\" [要強制搬的路徑…]}"
shift || true
# ⛔⛔ 2026-09-10 實際踩到的「綠燈但什麼都沒搬」：
#   `esb-repair` 那一趟把 2026-09-08 的興櫃列補回去，**檔案內容是對的**，
#   ⚠ 但那個結果與**分支上已經有的那一版逐位元組相同**
#   ⇒ 下面 `CHANGED` 是「本趟改到的檔」⇒ 它不在裡面 ⇒ **沒有被搬到 main**。
#   ⚠ 而整趟是綠的、log 也印著「保留其他市場的 2395 列」——看起來完全成功。
#
# ⭐ 根因：`CHANGED` 問的是「這一趟改了什麼」，
#   ⛔ 但有一種真實情形是「**分支與 main 本來就不同，而本趟不必改它**」。
#   ⇒ 呼叫端可以在第一個參數之後列出**一定要搬**的路徑。
#
# ⚠ 這個開關**會用分支的內容覆蓋 main 的**，所以：
#   ⛔ 只准用在「呼叫端剛剛才把 main 的那一份取下來當底稿」的步驟
#     （`esb-repair` 就是先 `git checkout origin/main -- <該日日檔>` 才跑的）。
#   ⛔ 不可以拿它來搬「分支上放了很久沒動」的檔——那正是第四點六那條的災情。
FORCE="$*"

git config user.name  "github-actions[bot]"
git config user.email "41898282+github-actions[bot]@users.noreply.github.com"

# ⭐ 要搬哪一棵樹。預設 `data`——⛔ 八支 workflow 全部靠預設值，不要改它。
#   `PUSH_TREES` 只給「輸出不在 `data/` 底下」的呼叫端用
#   （目前只有 `forward.yml`，它寫的是 `backtest/forward/`）。
#   ⚠ 為什麼不另寫一支推檔腳本：CLAUDE.md 四點五。⛔ 兩份推檔邏輯 ＝
#     其中一份會漏掉重試、漏掉逐鍵合併，而且**沒有人會發現**。
#   ⚠ 下面那些 `data/` 專屬的處理（`_last_run.md` 逐區塊合併、台帳逐鍵合併）
#     對別的樹就是**不匹配、不生效**，不會誤傷。
TREES="${PUSH_TREES:-data}"

# ★ 用 -A：`git add <路徑>` 在舊版 git 不會把「檔案被刪掉」記進暫存區，
#   而 purge 模式產出的**就是刪除**。
git add -A $TREES
if git diff --staged --quiet; then
  echo "[push_data] 沒有變動，不 commit"
  exit 0
fi
git commit -q -m "$MSG"

DC=$(git rev-parse HEAD)
BASE=$(git rev-parse HEAD~1)
LASTRUN="data/meta/_last_run.md"

# ⛔⛔ 累積型 CSV：**逐鍵合併，不可以整檔取本趟的**（2026-09-10 加）。
#
#   實際發生過的遺失：
#     07:15  一天實測（2026-09-09）推上 main ⇒ `_coverage_backfill.csv` 多一列
#     07:20  2015 那批開跑。它的 checkout 是**分支**，而分支上的 `data/`
#            **沒有**那一列（那一列是推到 main 的，不是推到分支）
#     07:22  它把整個檔搬到 main ⇒ ⛔ **五分鐘前那一列被刪掉**
#   ⚠ 而 `git diff` 看起來完全正常：一加一減，像是「這一趟重算過」。
#
# ⭐ 這跟下面 `_last_run.md` 那段是同一件事，只是它先被想到——
#   同一個道理原本只做了一半。
#
# ⚠ 這裡是**具名清單**，⛔ 不是「所有 CSV 都合併」：
#   `_missing_rows.csv`／`_notrade_days.csv` 那些是**每趟全量重算**的，
#   合併它們會把已經修好的舊列**復活**。
#   ⇒ 只有「這一趟只 append 自己那幾列」的檔才進這張清單。
#
# ⭐ 2026-09-12：清單裡可以放**萬用字元**，第二欄填 `json` 就走字典逐鍵合併。
#   `feeds` 的兩本台帳本來走的是「整檔取本趟的」——⛔ 同一個道理又只做了一半：
#     `_fetched.json`  逐月型：哪幾個月問過了
#     `_asked.json`    逐日型：哪幾天問到了但那天沒資料（⇒ 續跑的判準）
#   ⚠ 它們被回退的樣子看起來只是「多花幾分鐘重問」，
#   ⛔ 直到 `--limit` 分批補那種跑法**永遠補不完**為止。
#
# ⭐⭐ 2026-09-15：`backtest/forward/p4_types/` 那兩個檔（回測線 0141 §一）。
#   ⚠ 它們跟上面那幾個是**同一族**：由 main 上的 `forward.yml` 逐月 append
#   ⇒ 分支那份永遠比 main 舊 ⇒ ⛔ 整份取本趟的就是把新的月份刪掉。
#   ⚠ 而前瞻紀錄**補不回來**（重算出來的就不是前瞻了）⇒ 這一族刪了沒有第二次機會。
# ⭐⭐ 2026-09-19 加兩族，理由是同一句「**還沒發生不是判準**」：
#   `_official_monthly_done_*.csv`  月表掃描的續跑台帳（一趟 append 5,000 列）
#   `longhalt.csv`                  G2 每日累積（⛔ 這一族**補不回來**：
#                                   那三條端點只有當日，刪掉就是永久損失）
#   ⚠ 它們目前**只在 main 上被寫**（feeds／daily）⇒ 今天還沒有東西可以蓋掉它們
#   ——⛔ 而那正是 `_runs.jsonl` 當年沒被蓋掉的理由，而那是**運氣**。
# ⚠ 而 `merge_ledger` 要求兩邊**表頭相同** ⇒ 前提是 main 上那一份已經是新表頭
#   （`official_stats._upgrade_sweep_header()` 會在 append 之前先把它升上來）。
# ⛔ 而 `universe.csv` 的 `first_seen` 取小／`last_seen` 取大**這一份不做**：
#   逐鍵合併只保證那一列不會消失，⚠ 取小取大是 `forward_p4` 自己讀既有檔時算的。
#   ⇒ ⭐ 前提是它**在 main 上跑**（`forward.yml` 有一道「只准在 main 上跑」擋著），
#     而且 `sync_code.sh` 的 EXCLUDE_TREES 有 `backtest/forward`
#     ⇒ 分支那份不會反向蓋回去。⛔ 這三道缺一道，取小取大就會錯。
LEDGERS="
data/universe/_coverage_backfill.csv:date
data/meta/delisted.csv:market,stock_id,delist_date
data/meta/calendar_tpex.csv:date
data/meta/holiday_schedule.csv:date
data/universe/*/_fetched.json:json
data/universe/*/_asked.json:json
backtest/forward/p4_types/records.csv:measure_date,stock_id
backtest/forward/p4_types/universe.csv:stock_id
data/meta/_official_stats_done.csv:stock_id
data/meta/_official_stats_miss.csv:stock_id
data/meta/_official_monthly_done_*.csv:stock_id,roc_year
data/meta/longhalt.csv:src,stock_id,start_date,flags
data/early/_structure.csv:date,market
data/early/_revenue_structure.csv:period,market
data/meta/filing_dates.csv:stock_id,year,season,doc_code
data/meta/_filing_dates_asked.csv:stock_id,roc_year
data/mops/_rd_status.csv:period
"
CHANGED=$(git diff --name-only "$BASE" "$DC" -- $TREES)
if [ -n "$FORCE" ]; then
  for fp in $FORCE; do
    if printf '%s\n' "$CHANGED" | grep -qx "$fp"; then
      echo "[push_data] （$fp 本趟本來就改到了，不必強制）"
    else
      echo "[push_data] ⭐ 強制搬：$fp（本趟沒改到它，但分支與 main 不同）"
      CHANGED=$(printf '%s\n%s\n' "$CHANGED" "$fp")
    fi
  done
fi
DELETED=$(git diff --diff-filter=D --name-only "$BASE" "$DC" -- data)
echo "[push_data] 本趟改到 $(printf '%s\n' "$CHANGED" | grep -cv '^$') 個 data 檔"

for i in 1 2 3; do
  git fetch origin main || { sleep $((i * 5)); continue; }
  git checkout -q -B _push origin/main || break
  # 累積型的先排除，下面單獨逐鍵合併
  # ⚠ 清單裡可能有萬用字元 ⇒ 用 `case` 逐條比對，⛔ 不可以用 `grep -x`
  #   （`grep -x 'data/universe/*/_asked.json'` 比的是**字面**，永遠不中，
  #     ⇒ 那些檔會走到下面的整檔取代，而那正是這一段要防的事）
  KEEP=""
  for f in $(printf '%s\n' "$CHANGED" | grep -v '^$' | grep -vx "$LASTRUN"); do
    hit=""
    for ent in $(printf '%s\n' "$LEDGERS" | grep -v '^$'); do
      case "$f" in ${ent%%:*}) hit=1; break ;; esac
    done
    [ -n "$hit" ] || KEEP=$(printf '%s\n%s' "$KEEP" "$f")
  done
  # ⛔⛔ 2026-09-15 付過代價（probe run 101）：這裡本來是**一整批**
  #   `xargs -r git checkout "$DC" -- <23 個路徑>`。
  #   ⚠ 其中一個（`data/meta/_ci_steps.tsv`）在本趟被**刪掉**了
  #   ⇒ `error: pathspec … did not match any file(s) known to git`
  #   ⇒ ⭐ **整批失敗 ⇒ 另外 22 個檔一個都沒有被取出來**
  #   ⇒ 那一趟照樣 commit、照樣 push、照樣印「✓ 已推上 main」，
  #     ⛔ 而 main 上只多了 `_last_run.md`——**探針輸出一個都沒搬過去**。
  #   ⚠ 而它跟四點六那條是同一族：**「推成功了」≠「東西搬過去了」**。
  # ⇒ 兩件：① 刪掉的路徑不進 KEEP（它們由下面那行 `git rm` 處理）
  #        ② ⭐ 一個一個取，並且**記下失敗**——⛔ 靜靜跳過就是這次的病根
  CKFAIL=0
  for f in $(printf '%s\n' "$KEEP" | grep -v '^$'); do
    case " $(printf '%s ' $DELETED) " in *" $f "*) continue ;; esac
    git checkout "$DC" -- "$f" || { echo "[push_data] ⛔ 取不出來：$f" >&2
                                    CKFAIL=$((CKFAIL + 1)); }
  done
  if [ "$CKFAIL" -gt 0 ]; then
    echo "[push_data] ⛔⛔ 有 $CKFAIL 個檔沒搬過去 ⇒ **這一趟算失敗**" >&2
    echo "[push_data] ⚠ ⛔ 不可以照樣 push：那會印「✓ 已推上 main」而東西沒到" >&2
    git checkout -q "${GITHUB_REF_NAME:-main}" 2>/dev/null || true
    exit 3
  fi
  printf '%s\n' "$DELETED" | grep -v '^$' \
    | xargs -r git rm -q -f --ignore-unmatch
  # ⚠ `_last_run.md` 是**跨 workflow 累積**的（runlog 只覆蓋自己那一區塊）
  #   ⇒ ⛔ 不可以整份取本趟的，否則另一支剛報的 ✗ 會被安靜換回上一輪的 ✓。
  if printf '%s\n' "$CHANGED" | grep -qx "$LASTRUN"; then
    git show "$DC:$LASTRUN" > /tmp/lr_mine.md
    git show "origin/main:$LASTRUN" > /tmp/lr_main.md 2>/dev/null || : > /tmp/lr_main.md
    if python3 merge_last_run.py /tmp/lr_mine.md /tmp/lr_main.md > "$LASTRUN"; then
      git add -- "$LASTRUN"
    else
      echo "[push_data] ⛔ _last_run.md 逐區塊合併失敗，取本趟的（⚠ 另一支的區塊可能被回退）" >&2
      git checkout "$DC" -- "$LASTRUN" && git add -- "$LASTRUN"
    fi
  fi
  # ⭐ 累積型 CSV：逐鍵合併（本趟的鍵覆蓋、main 的其餘列原封不動保留）
  for ent in $(printf '%s\n' "$LEDGERS" | grep -v '^$'); do
    LK=${ent#*:}
    for LP in $(printf '%s\n' "$CHANGED" | grep -v '^$'); do
      case "$LP" in ${ent%%:*}) ;; *) continue ;; esac
      git show "$DC:$LP" > /tmp/lg_mine.dat 2>/dev/null || continue
      git show "origin/main:$LP" > /tmp/lg_main.dat 2>/dev/null || : > /tmp/lg_main.dat
      # ⭐ 2026-09-25：同目錄有 `<檔名去 .csv>.remove.csv` ⇒ 當移除清單（只刪清單上逐字列出的鍵）
      RMF=""
      if git show "$DC:${LP%.csv}.remove.csv" > /tmp/lg_rm.dat 2>/dev/null; then RMF=/tmp/lg_rm.dat; fi
      if python3 merge_ledger.py /tmp/lg_mine.dat /tmp/lg_main.dat "$LK" $RMF > /tmp/lg_out.dat; then
        cp /tmp/lg_out.dat "$LP"
        git add -- "$LP"
      else
        # ⛔ 合併不成就**整檔取本趟的**，⚠ 但一定要吼出來：
        #   那正是會靜靜刪掉別人剛寫的列的那條路。
        echo "[push_data] ⛔ $LP 逐鍵合併失敗，退回整檔取本趟的（⚠ main 上較新的可能被回退）" >&2
        git checkout "$DC" -- "$LP" && git add -- "$LP"
      fi
    done
  done
  git add -A $TREES
  if git diff --staged --quiet; then
    echo "[push_data] 搬到 main 之後沒有差異（多半是別的 workflow 已推過同樣內容）"
    git checkout -q "${GITHUB_REF_NAME:-main}" 2>/dev/null || true
    exit 0
  fi
  # ⭐⭐ 要驗收的那幾個路徑，**在 commit 之前**先記下來（K線分析線〈七十二〉）。
  STAGED=$(git diff --staged --name-only --diff-filter=d)
  git commit -q -m "$MSG"
  if git push origin HEAD:main; then
    # ══════════════════════════════════════════════════════════════
    # ⛔⛔ **「✓ 已推上 main」原本是一行 echo，不是證據**（K線分析線 2026-09-15
    #   〈七十二〉，而它是拿 2026-09-15 那件實際事故寫出來的：probe run 101
    #   印了「✓ 已推上 main」，⚠ 而那一趟寫出來的 22 份探針輸出**一份都沒到**。）
    #
    # ⭐ 判別法一句話：**把那個步驟的實際動作註解掉，成功訊息還會不會印？**
    #   會印 ⇒ ⛔ 它不是證據，是一行 echo。
    #   ⚠ 而原本這一行在 `git push` 回 0 的時候就印了
    #   ⇒ 它證明的是「push 這個命令成功了」，⛔ **不是「那些檔到了 main」**。
    #     （那次 push 確實成功——⚠ 只是 commit 裡根本沒有那 22 個檔。）
    #
    # ⇒ ⭐ 改成**從 main 讀回來**：fetch 之後逐檔比 blob sha。
    #   ⛔ 不比 commit sha：別人可能在這幾秒也推了 main，main 會往前走
    #   ⇒ 我們的 commit 變成祖先，而那是**正常**的。
    #   ⚠ 而「別人推的那一趟改了同一個檔」也是正常的 ⇒ 那種情況下 blob 會不同，
    #     ⭐ 所以對不上時要先看我們的 commit 還在不在 main 的歷史裡：
    #     在 ⇒ 是被後來的人覆蓋（吼一聲，⛔ 不算這一趟失敗）
    #     不在 ⇒ ⛔⛔ 這一趟真的沒到 ⇒ **失敗**
    # ══════════════════════════════════════════════════════════════
    MYC=$(git rev-parse HEAD)
    if ! git fetch -q origin main 2>/dev/null; then
      echo "[push_data] ⚠⚠ **讀回驗證這一層沒跑**：fetch origin main 失敗" >&2
      echo "   ⇒ ⛔ 不算失敗（push 本身回 0），⛔ **也不算驗過**" >&2
    else
      BAD=0
      for f in $(printf '%s\n' "$STAGED" | grep -v '^$'); do
        A=$(git rev-parse "$MYC:$f" 2>/dev/null || echo "-")
        B=$(git rev-parse "origin/main:$f" 2>/dev/null || echo "-")
        [ "$A" = "$B" ] && continue
        BAD=$((BAD + 1))
        echo "[push_data] ⛔ main 上那一份跟我推的不一樣：$f（我 $A｜main $B）" >&2
      done
      if [ "$BAD" -gt 0 ]; then
        if git merge-base --is-ancestor "$MYC" origin/main 2>/dev/null; then
          echo "[push_data] ⚠ 我的 commit 在 main 的歷史裡 ⇒ 上面 $BAD 個是被**後來的人**改的" >&2
          echo "   ⇒ ⛔ 不算這一趟失敗，⚠ 而它值得看一眼（誰在同一秒改了同一個檔）" >&2
        else
          echo "[push_data] ⛔⛔ 而我的 commit **不在 main 的歷史裡** ⇒ 這一趟根本沒到" >&2
          git checkout -q "${GITHUB_REF_NAME:-main}" 2>/dev/null || true
          exit 5
        fi
      fi
      NV=$(printf '%s\n' "$STAGED" | grep -vc '^$' || true)
      echo "[push_data] ✓ 已推上 main（⭐ 從 main 讀回來逐檔比過：$NV 個檔的 blob sha）"
      git checkout -q "${GITHUB_REF_NAME:-main}" 2>/dev/null || true
      exit 0
    fi
    echo "[push_data] ✓ 已推上 main（⚠ 讀回那一層沒跑，見上）"
    # ⛔ 一定要切回原本的分支：呼叫端後面可能還要繼續跑。
    git checkout -q "${GITHUB_REF_NAME:-main}" 2>/dev/null || true
    exit 0
  fi
  echo "[push_data] push 失敗（第 $i 次），多半是這幾秒又有人推了 main，重來" >&2
  sleep $((i * 5))
done
echo "[push_data] ⛔ 連續三次 push 失敗" >&2
exit 1

#!/usr/bin/env bash
# sync_code.sh — 把**分支上的程式**搬到 main 的頭上，然後推。
#
# 用法：  bash sync_code.sh
# 回傳：  一律 0（同步失敗不該讓呼叫端整趟紅——它只是「這一趟沒同步」）
#
# ⛔⛔ 為什麼要有這個檔：這段本來在**八支 workflow 各抄一份**，逐字相同。
#   2026-09-13 要在它裡面加一份排除清單，⚠ 而八份各改一次
#   ＝「改一邊、另一邊沒跟上」的完美條件。⇒ CLAUDE.md 四點五：只留一份。
#
# ⛔⛔ 2026-09-10：這一步的第一版寫成 `git rebase origin/main`，
#   而它跟那個丟掉 5 小時的 bug 是同一個病：rebase 會重放分支上所有
#   還沒進 main 的 commit，撞上 main 現在的內容。
#   ⇒ 實測（run 34426373917）：它 abort 了、`continue-on-error` 讓它顯示成功，
#     而 **main 上的程式一個字都沒更新**——而排程跑的正是 main 上的程式。
#   ⚠ 失敗的樣子：這一步是**綠的**，只是什麼都沒做。
#
# ⇒ 改成跟 `push_data.sh` 對稱的做法：把**程式路徑**搬到 main 的頭上，不 rebase。
#   ① 不重放任何 commit ⇒ 永遠不會衝突
#   ② 排除清單裡的樹完全不碰 ⇒ 別人剛寫的東西原封不動
set -u

# ══════════════════════════════════════════════════════════════════
# ⭐⭐ 排除清單 ＝ **「main 是唯一寫入者」的樹**
#
# ⛔ 判準不是「這是不是資料」，是**「誰寫它」**：
#   凡是由 workflow 在 main 上產生、而且**累積**的東西，
#   分支上那一份永遠是舊的 ⇒ 搬過去就是把新的蓋掉。
#
# ⚠ 2026-09-13 付過代價（回測線 09:05 抓到）：
#   `forward.yml` 在 main 上寫了 `backtest/forward/runlog.md` 的 02:42 區塊，
#   ⇒ 我 03:00 這一步把**分支上那份舊的**搬過去 ⇒ 那一塊被刪掉（−4 行）。
#   ⛔ 而 `git diff` 看起來完全正常，⚠ 而那一趟是綠的。
#   ⭐ 這正是 CLAUDE.md 四點六，只是主詞從 `data/` 換成 `backtest/forward/`。
#
# ⚠ `_runs.jsonl` 當時**沒有**被蓋掉——⛔ 而那是運氣：
#   只因為分支上根本沒有那個檔。**「還沒發生」不是判準。**
# ══════════════════════════════════════════════════════════════════
EXCLUDE_TREES="
data
backtest/forward
"

BR="${GITHUB_REF_NAME:-main}"
if [ "$BR" = "main" ]; then echo "本來就在 main，不必同步"; exit 0; fi
git config user.name  "github-actions[bot]"
git config user.email "41898282+github-actions[bot]@users.noreply.github.com"

SPEC=""
for T in $EXCLUDE_TREES; do SPEC="$SPEC :(exclude)$T"; done
echo "[sync_code] 排除（main 是唯一寫入者）：$(echo $EXCLUDE_TREES | tr '\n' ' ')"

SRC=$(git rev-parse HEAD)
# ⛔⛔ 2026-09-15 補：`git push … && echo "✓ …"` 的失敗**沒有人接**
#   ⇒ push 被別人搶先、被拒絕、網路掉，這支照樣 `exit 0`，
#     ⚠ 而畫面上只是**少了一行成功訊息** ⇒ ⛔ 沒有任何地方會說。
#   ⭐ 而 probe.yml 的註解早就寫著這件事該怎麼辦：
#     「走到 push 還失敗就是**真的有問題**，該紅。」
# ⇒ 重試 3 次（⚠ 搶先是常態：daily／feeds 一直在推 main，
#   一次就紅會變成一道天天紅的閘門），⭐ 三次都不成才 exit 4。
# ⚠ 為什麼不跟 `push_data.sh` 共用那個重試迴圈：那一份的迴圈體是
#   **逐檔搬資料 ＋ 逐鍵合併台帳**，這裡是**整棵程式樹**，兩邊的重建動作不同。
#   ⛔ 硬湊成一份會多出一堆「這一邊不適用」的分支——那比兩份更難改。
SYNCED=0
for i in 1 2 3; do
  git fetch origin main || { echo "⚠ fetch main 失敗，跳過同步" >&2; exit 0; }
  git checkout -q -B _sync origin/main || { echo "⚠ 切不過去" >&2; exit 0; }
  # shellcheck disable=SC2086
  git checkout "$SRC" -- . $SPEC || {
    echo "⚠ 取程式路徑失敗，跳過同步" >&2; git checkout -q "$BR" 2>/dev/null; exit 0; }

  # ⭐ `backtest/forward/RULE.md` 是**回測線寫的判準檔**，⛔ 不是紀錄檔
  #   ⇒ 它要跟著同步。⚠ 而同一個目錄裡的 runlog／state 是 main 寫的，上面已排除。
  #   ⛔ 不要因為「同一個目錄」就一起排除——那會讓 RULE.md 永遠到不了 main。
  if git cat-file -e "$SRC:backtest/forward/RULE.md" 2>/dev/null; then
    git checkout "$SRC" -- backtest/forward/RULE.md \
      && echo "[sync_code] ⭐ 例外放行：backtest/forward/RULE.md（判準檔，回測線寫的）"
  fi

  git add -A
  if git diff --staged --quiet; then
    echo "程式已經跟 main 一致，沒有要同步的"
    SYNCED=1
    break
  fi
  git commit -q -m "sync: 把分支的程式同步到 main"
  if git push origin HEAD:main; then
    echo "✓ 程式已同步到 main"
    SYNCED=1
    break
  fi
  echo "[sync_code] push 失敗（第 $i 次），多半是這幾秒又有人推了 main，重來" >&2
  sleep $((i * 5))
done
if [ "$SYNCED" -ne 1 ]; then
  echo "[sync_code] ⛔⛔ 三次都推不上去 ⇒ **main 上的程式沒有更新**" >&2
  echo "[sync_code] ⚠ 而排程跑的是 main 上那一份 ⇒ ⛔ 這一趟之後的排程跑的是舊程式" >&2
  git checkout -q "$BR" 2>/dev/null || git checkout -q "$SRC"
  exit 4
fi
# ⛔ 一定要切回原本的分支：後面的步驟（回補、Commit）都靠它。
git checkout -q "$BR" 2>/dev/null || git checkout -q "$SRC"
exit 0

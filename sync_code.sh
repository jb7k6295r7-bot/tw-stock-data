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
LAST_ERR=""
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

  # ══════════════════════════════════════════════════════════════════
  # ⭐⭐ **刪除也要搬過去**（2026-09-16 付過代價）
  #
  # 上面那兩行只會**新增／覆蓋**：`git checkout "$SRC" -- .` 把分支有的檔
  # 蓋到 main 的頭上，⛔ 而 **main 有、分支沒有**的檔它一個字都不碰。
  # ⇒ 分支上刪掉一個檔，那個檔**永遠留在 main 上**。
  #
  # ⚠ 實際代價：`site_recon.py` 2026-09-13 在分支上刪掉了
  #   （CLAUDE.md 四點五第七次：我重造了一份 `site_inventory.py`），
  #   ⛔ 而 main 上那一份一直在 ⇒ 2026-09-16 probe run 126 的
  #   `selftest_probes.py` 在 main 上 **rc=1**（母體 21 支、沒叫的就是它），
  #   ⚠ 而同一支自測在分支上是**綠的** ⇒ 同一支程式、同一天、兩個答案。
  # ⇒ ⭐ 這是四點六那一族的**鏡像**：那邊是「分支的檔比 main 舊」，
  #   這邊是「**分支沒有那個檔**」——⛔ 而兩邊的畫面都是一趟綠的同步。
  #
  # ⛔⛔ 而刪除是這支唯一會**毀掉東西**的動作 ⇒ 三道閘門，缺一道都不刪：
  #   ① 排除樹底下的路徑**一個都不准**出現在刪除清單裡（⚠ `data/` 是資料）
  #   ② 一趟最多刪 $MAX_DEL 個——⭐ 超過就**一個都不刪**並大聲印，
  #      ⛔ 但**不算失敗**：新增／覆蓋照常搬（六點五：跳過的那一層要出聲）
  #   ③ 逐一刪、記下失敗、**有失敗就不往下走**（四點二⑥：一批裡一個壞元素
  #      會毒死整批——`push_data.sh` 的 `xargs` 就是那樣掉了 22 個檔）
  #      ⚠ 而要**標清楚**：③ 真正守門的是「有失敗就不往下走」那一半。
  #      ⛔ 「逐一 vs 整批」這一半**量不到**——實測突變 D6（改成
  #      `git rm -- $DEL` 整批）⇒ `selftest_push_data.py` ⑧ 照樣全綠，
  #      因為兩種寫法在「有壞元素」時都走到 exit 5 ⇒ main 都沒被推成半套。
  #      ⇒ ⭐ 那不是「那條斷言沒用」，是**那個突變什麼都沒改變**（第七點第四個）。
  #      逐一寫法留著的理由只有一個：它講得出**是哪一個**刪不掉。
  # ══════════════════════════════════════════════════════════════════
  MAX_DEL=20
  # shellcheck disable=SC2086
  DEL=$(git diff --name-only --no-renames --diff-filter=D origin/main "$SRC" -- . $SPEC)
  NDEL=$(printf '%s\n' "$DEL" | grep -c . || true)
  BAD=$(printf '%s\n' "$DEL" | grep -E '^(data|backtest/forward)/' || true)
  if [ -n "$BAD" ]; then
    echo "[sync_code] ⛔⛔ 刪除清單裡出現**排除樹**底下的路徑 ⇒ 一個都不刪：$BAD" >&2
  elif [ "$NDEL" -gt "$MAX_DEL" ]; then
    echo "[sync_code] ⛔⛔ 這一趟要刪 $NDEL 個檔（上限 $MAX_DEL）⇒ **一個都不刪**" >&2
    echo "[sync_code] ⚠ **這一層沒跑**：刪除沒有同步（新增／覆蓋照常）" >&2
  elif [ "$NDEL" -gt 0 ]; then
    RMFAIL=""
    while IFS= read -r f; do
      [ -n "$f" ] || continue
      if git rm -q -f -- "$f"; then
        echo "[sync_code] ⭐ 刪除同步到 main：$f"
      else
        RMFAIL="$RMFAIL $f"
      fi
    done <<EOF
$DEL
EOF
    if [ -n "$RMFAIL" ]; then
      echo "[sync_code] ⛔⛔ 這幾個刪不掉：$RMFAIL ⇒ **不往下走**（半套的同步比沒同步糟）" >&2
      git checkout -q "$BR" 2>/dev/null || git checkout -q "$SRC"
      exit 5
    fi
  fi

  git add -A
  if git diff --staged --quiet; then
    echo "程式已經跟 main 一致，沒有要同步的"
    SYNCED=1
    break
  fi
  git commit -q -m "sync: 把分支的程式同步到 main"
  # ⛔⛔ 2026-09-16 probe run 129 付過代價：這一步 **failure**（50 秒 ＝ 三次都沒推上），
  #   ⚠ 而同樣的內容 run 130 一次就推成功 ⇒ 那是**一次性**的。
  #   ⭐ 而真正的問題不是它失敗，是**我事後查不出原因**：
  #     Actions 的 job log API 只回得到**尾段**，而這一步在很前面
  #     ⇒ 等到我發現紅燈時，那幾行 git 的錯誤訊息已經拿不到了。
  #   ⇒ ⭐ 把 push 的 stderr 接住並印在**最後那段失敗訊息裡**——
  #     ⛔ 這樣它就跟 `exit 4` 那幾行在一起，⚠ 而那幾行在尾段。
  PUSH_ERR=$(git push origin HEAD:main 2>&1) && PUSH_OK=1 || PUSH_OK=0
  printf '%s\n' "$PUSH_ERR"
  if [ "$PUSH_OK" = "1" ]; then
    echo "✓ 程式已同步到 main"
    SYNCED=1
    break
  fi
  echo "[sync_code] push 失敗（第 $i 次），多半是這幾秒又有人推了 main，重來" >&2
  LAST_ERR="$PUSH_ERR"
  sleep $((i * 5))
done
if [ "$SYNCED" -ne 1 ]; then
  echo "[sync_code] ⛔⛔ 三次都推不上去 ⇒ **main 上的程式沒有更新**" >&2
  echo "[sync_code] ⚠ 而排程跑的是 main 上那一份 ⇒ ⛔ 這一趟之後的排程跑的是舊程式" >&2
  # ⭐ 把最後一次的 git 訊息原文印在這裡（⛔ 不砍尾巴，六點六那條）
  echo "[sync_code] ⇒ 最後一次 git push 的原文：" >&2
  printf '%s\n' "${LAST_ERR:-（沒接到訊息）}" >&2
  git checkout -q "$BR" 2>/dev/null || git checkout -q "$SRC"
  exit 4
fi
# ⛔ 一定要切回原本的分支：後面的步驟（回補、Commit）都靠它。
git checkout -q "$BR" 2>/dev/null || git checkout -q "$SRC"
exit 0

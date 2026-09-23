#!/usr/bin/env bash
# ⭐⭐ 回測線交接驗收：讓【機器】回答「接手的環境沒問題嗎」，⛔ 不是讓任何一個人回答。
#
# ⛔ 這支【不改任何東西】：
#   ・P16 跑進【暫存目錄】⇒ ⛔ 絕不寫 backtest/resultsp16/
#     （CLAUDE.md 四點六：累積型／交件型的目錄不可以被一趟重算整份覆蓋）
#   ・只讀、只比、只回 exit code
#
# ⭐ 判準一律驗【終點】，⛔ 不驗中間（CLAUDE.md 四點二）：
#   ⛔ 不斷言「自測跑完了」⇒ ⭐ 斷言 rc==0 且輸出裡沒有 ✗
#   ⛔ 不斷言「P16 跑完了」⇒ ⭐ 斷言 15 個輸出檔與交件【逐位元相同】
#
# 用法： bash backtest/handover_check.sh
#   ⚠ 約 10 分鐘（閘門 ~2 分 ＋ P16 全量重現 ~7 分）
set -uo pipefail
cd "$(dirname "$0")/.." || exit 2
FAIL=0
note(){ printf '%s\n' "$*"; }
bad(){ FAIL=$((FAIL+1)); printf '⛔ %s\n' "$*"; }

note "════ 〇、新 session 進來第一件事（CLAUDE.md 六點五）════"
# ⛔⛔ 2026-09-22 訂正（接手方指出）：這裡本來直接 `git config core.hooksPath .githooks`
#   ⇒ ⚠ 而檔頭寫著「這支【不改任何東西】」⇒ ⭐ 那是一句【自己打自己】的話
#   ⇒ ✅ 改成【只檢查、不設定】：要不要設定是跑的人的決定，⛔ 不是驗收腳本偷偷做掉
HP=$(git config --get core.hooksPath || true)
if [ "$HP" = ".githooks" ]; then note "✅ core.hooksPath ＝ .githooks"
else
  bad "core.hooksPath ＝ '${HP:-(未設)}' ⇒ ⛔ pre-commit 不會跑"
  note "   ⇒ ⭐ 請自己執行一次：git config core.hooksPath .githooks"
  note "   ⇒ ⚠ 少了它，壞掉的那一刻不會有人叫（CLAUDE.md 六點五）"
fi

note ""
note "════ 〇之二、⛔⛔ 輸入盤點（⭐ 2026-09-22 補：少了這一段，紅燈的【診斷會是錯的】）════"
# ⚠ 這一段是【接手方問出來的】：backtest/resultsp4/panel.csv.gz 被 .gitignore 排除
#   ⇒ ⛔ 新 clone 拿不到 ⇒ 第二段會失敗在「P16 沒跑完」，⚠ 看起來像環境壞了
#   ⇒ ⭐ 而真正的原因是【輸入沒有版控】—— 兩者的處置完全相反
BASE=backtest/HANDOVER_BASELINE.txt
[ -f "$BASE" ] || { bad "缺基準線 $BASE ⇒ ⛔ 無法分辨紅燈是輸入不同還是引擎不同"; }
INPUT_DRIFT=0
FILE_ROWS=0
if [ -f "$BASE" ]; then
  while read -r want tracked f; do
    # ⛔⛔ 2026-09-22 訂正（接手方實測抓到）：這裡本來是【負面排除】
    #   case "$want" in '#'*|deliverable_commit|branch) continue;; esac
    #   ⇒ ⚠ 而本線在 〇之三 往基準線加了 env_* 與 procs_used【卻沒有同步這份清單】
    #   ⇒ ⛔ 那 4 列被當成檔案列 ⇒ f 是空字串 ⇒ 判「不存在」⇒ FAIL 至少 4
    #     ⭐ 也就是【這道檢查不可能回綠】，就算環境完美無瑕
    #   ⇒ ⛔ 而它印出來的 bad 連檔名都是空的 ⇒ 紅燈【無法診斷】
    # ⭐⭐ 改成【正面挑選】：只有第二欄宣告 tracked／UNTRACKED 的才是檔案列
    #   ⇒ 往後基準線再加任何新鍵，這裡都不必跟著改（⛔ 這才是把那一族殺掉，不是補這一次）
    case "$tracked" in tracked|UNTRACKED) ;; *) continue;; esac
    FILE_ROWS=$((FILE_ROWS+1))
    printf '  %-44s ' "$f"
    if [ ! -f "$f" ]; then
      echo "⛔⛔ 不存在"
      if [ "$tracked" = "UNTRACKED" ]; then
        bad "$f 【沒有版控】且不存在 ⇒ ⛔ 這不是環境壞了，是新 clone 本來就拿不到"
        note "     ⇒ ⭐ 它由 researchp4 產生（約 24 MB，被 .gitignore 排除）"
        note "     ⇒ ⛔ 在它補上之前，第二段【跑不起來】，⚠ 而失敗訊息會長得像環境問題"
      else
        bad "$f 有版控卻不存在 ⇒ ⛔ 這個 checkout 不完整"
      fi
      continue
    fi
    got=$(sha256sum "$f" | cut -c1-64)
    if [ "$got" = "$want" ]; then echo "✅ 與交件同一份"
    else echo "⚠ 與交件【不同】"; INPUT_DRIFT=$((INPUT_DRIFT+1))
         note "     want $want"; note "     got  $got"; fi
  done < "$BASE"
fi
note "  （基準線裡的檔案列：$FILE_ROWS 列）"
[ "$FILE_ROWS" -gt 0 ] || bad "基準線一列檔案都沒解析到 ⇒ ⛔ 這不是「通過」，是【沒驗到】"
if [ "$INPUT_DRIFT" -gt 0 ]; then
  note ""
  note "⛔⛔ 有 $INPUT_DRIFT 個輸入與交件【不是同一份】"
  note "   ⇒ ⭐ 那麼第二段【對不上是預期的】，⛔ 它不代表引擎或環境有問題"
  note "   ⇒ ⚠ 而【對得上】也不能讀成「資料對齊」—— 那只是這幾天的差異剛好不影響窗內"
  note "   ⇒ ⏳ 這種情形要先定【以哪一份輸入為準】，⛔ 不可以直接讀這道檢查的顏色"
fi

note ""
note "════ 〇之三、⛔⛔ 執行環境（⭐ 2026-09-22 補：接手方指出，⛔ 本線原本一格都沒釘）════"
# ⚠ 逐位元比對對 Python／numpy／pandas 版本極度敏感 ⇒ ⛔ 不釘住，紅燈的歸因就是錯的
ENV_DRIFT=0
if [ -f "$BASE" ]; then
  while read -r k want; do
    case "$k" in env_*) ;; *) continue;; esac
    got=$(python3 - "$k" <<'PYV' 2>/dev/null || echo "(取不到)"
import sys, os
k = sys.argv[1]
if k == "env_python": print(sys.version.split()[0])
elif k == "env_numpy": import numpy; print(numpy.__version__)
elif k == "env_pandas": import pandas; print(pandas.__version__)
# ⭐ 2026-09-23 補（接手方 0210 指出）：BLAS 名稱＋版本與執行緒數都會影響浮點的歸約順序
#   ⛔ 本線原本一格都沒釘 ⇒ ⚠ 上一趟是【碰巧兩台都對上】才沒出事
elif k == "env_blas":
    import numpy
    b = numpy.__config__.show(mode="dicts")["Build Dependencies"]["blas"]
    print(f"{b.get('name')}-{b.get('version')}")
elif k == "env_blas_threads":
    print(os.environ.get("OPENBLAS_NUM_THREADS") or os.cpu_count())
PYV
)
    printf '  %-16s ' "${k#env_}"
    if [ "$got" = "$want" ]; then echo "$got　✅ 與交件相同"
    else echo "$got　⚠ 交件是 $want"; ENV_DRIFT=$((ENV_DRIFT+1)); fi
  done < "$BASE"
fi
note "  procs            本趟 ${PROCS:-8}（⭐ 交件用 8；⚠ 已實測 procs 不影響輸出，見 HANDOVER.md）"
note "  ⚠ blas_threads 是【推得出來的】：OPENBLAS_NUM_THREADS 未設時退回 cpu_count()"
note "    ⇒ ⛔ 不是量到的實際執行緒數 ⇒ ⭐ 它對得上只代表【推論值】對得上"
# ⛔⛔ 2026-09-22 補（接手方問 WSL 時查出來的）：researchp16 的 run() 那兩個 Pool
#   【沒有 initializer】⇒ worker 拿到 _P 完全靠 fork 繼承
#   ⇒ ⛔ spawn 之下 _P 是空的 ⇒ KeyError: 'sigs' ⇒ ⭐ 這是【前置條件】，不是效能建議
SM=$(python3 -c "import multiprocessing as m;print(m.get_start_method())" 2>/dev/null || echo "(取不到)")
printf '  %-16s %s' "start_method" "$SM"
if [ "$SM" = "fork" ]; then echo "　✅ 可以跑"
else
  echo "　⛔⛔ 跑不起來"
  bad "start_method ＝ '$SM' ⇒ ⛔ researchp16 依賴 fork 繼承 _P"
  note "   ⇒ ⛔ spawn（Windows 原生 Python／macOS 3.8+）與 forkserver（Linux + Python 3.14）都不行"
  note "     ⭐ 兩種都【已實測】：同樣死在 researchp16.py:317 ⇒ KeyError: 'sigs'"
  note "   ⇒ ✅ 交件指定的 Python 3.11.15 在 Linux 上預設正好是 fork"
  note "     ⇒ ⭐ 裝對版本，【版本對齊】與【fork 前置條件】一次滿足"
  note "   ⚠ 而它【會先印出六行綠的】（fixture／sig／逐日／回聲閘門／四個臂）才死"
  note "     ⇒ ⭐ 死在 [否證①] 那一步，訊息是 KeyError: 'sigs'（⛔ 大聲失敗，不是靜默算錯）"
  note "     ⇒ ⛔ 不要因為前面六行是綠的就以為「大致上跑起來了」"
fi
if [ "$ENV_DRIFT" -gt 0 ]; then
  note ""
  note "⚠ 有 $ENV_DRIFT 項版本與交件不同 ⇒ ⭐ 那麼第二段的結果要這樣讀："
  note "   ・版本不同【而且】逐位元相同 ⇒ ✅✅ 比交件方知道的更強（⭐ 表示結果不靠特定版本）"
  note "   ・版本不同【而且】對不上　　 ⇒ ⛔ 本趟【分不出】是引擎不同還是版本不同"
  note "     ⇒ ⏳ 要判引擎有沒有問題，必須先把版本裝成與交件相同再跑一次"
  note "   ⇒ ⛔ 在那之前，⛔ 不可以把紅燈讀成「接手方的環境壞了」"
fi

note ""
note "════ 一、閘門 ════"
# ⭐ 回測線那 9 支【用 glob 取】，⛔ 不在這裡列第二份清單（CLAUDE.md 四點五）
#   而「每一支 selftest_*.py 都有人跑」由 selftest_workflows.py 雙向保證 ⇒ ⛔ 這裡不重做那件事
GATES=()
for f in backtest/selftest_*.py; do GATES+=("backtest.$(basename "$f" .py)"); done
# ⭐ 另加 CLAUDE.md 逐字指名的兩道【常駐】閘：四點五（不准有第二份實作）／六點五（shell 語法）
for m in "${GATES[@]}"; do
  printf '  %-34s ' "$m"
  out=$(python3 -m "$m" 2>&1); rc=$?
  n=$(printf '%s' "$out" | grep -c '^  ✗')
  if [ $rc -ne 0 ] || [ "$n" -gt 0 ]; then echo "⛔ (rc=$rc ✗=$n)"; bad "$m"; printf '%s\n' "$out" | tail -12
  else echo "✅"; fi
done
for s in selftest_no_dup.py selftest_workflows.py; do
  printf '  %-34s ' "$s"
  out=$(python3 "$s" 2>&1); rc=$?
  if [ $rc -ne 0 ]; then echo "⛔ (rc=$rc)"; bad "$s"; printf '%s\n' "$out" | tail -12
  else echo "✅ $(printf '%s' "$out" | tail -1)"; fi
done

note ""
note "════ 二、⭐⭐ PREREGP16 全量重現（⛔ 這一道才是真的驗收）════"
REF=backtest/resultsp16
if [ -n "${P16_REUSE_OUT:-}" ]; then
  OUT="$P16_REUSE_OUT"
  note "⛔⛔ P16_REUSE_OUT 已設 ⇒ 本趟【沒有重跑】，只測比對邏輯本身"
  note "   ⇒ ⛔ 所以本趟【一律判不通過】，⭐ 它不可能被拿來假裝通過"
  FAIL=$((FAIL+1))
else
  OUT=$(mktemp -d)
  note "  跑：python3 -m backtest.researchp16 --reps 200 --rrand 30 --out $OUT"
  note "  ⚠ 約 7 分鐘；⛔ 輸出進暫存目錄，⛔ 不碰 $REF"
  if ! python3 -m backtest.researchp16 --reps 200 --rrand 30 --procs "${PROCS:-8}" --out "$OUT" > "$OUT/run.log" 2>&1; then
    bad "P16 沒跑完 ⇒ 見 $OUT/run.log"; tail -20 "$OUT/run.log"
  fi
fi

# ⭐ 驗終點：15 個輸出檔逐位元比對（⛔ 不是「跑完了」，⛔ 也不是「筆數對」）
same=0; diff_n=0; miss=0
for f in "$REF"/*.csv; do
  b="$OUT/$(basename "$f")"
  if   [ ! -f "$b" ];      then miss=$((miss+1));   bad "重現的輸出少了 $(basename "$f")"
  elif cmp -s "$f" "$b";   then same=$((same+1))
  else diff_n=$((diff_n+1)); bad "$(basename "$f") 與交件【不同】"; fi
done
note ""
note "  逐位元相同 $same／不同 $diff_n／缺 $miss　（交件共 $(ls "$REF"/*.csv | wc -l) 個 csv）"
[ "$same" -gt 0 ] || bad "一個都沒比到 ⇒ ⛔ 這不是「通過」，是【沒驗到】"

note ""
note "════ 三、結果 ════"
if [ "$FAIL" -eq 0 ]; then
  note "✅ 通過：閘門全綠 ＋ P16 的 15 個輸出檔與交件逐位元相同"
  note "⇒ ⭐ 它證明的是：**在【與交件同一份輸入】之下，引擎與隨機源逐位元一致**"
  note "⛔⛔ 它【不證明】資料是對的、也不證明資料是最新的"
  note "   ⇒ ⚠ 原本這一行寫「環境、資料、隨機源、引擎四樣都對齊」——【資料那一項是多講的】"
  note "     ⭐ 輸入由上面那一段【釘住】，⛔ 不是由這一段證明的（2026-09-22 訂正）"
  note "⛔ 它也【不證明】接手的人懂這些規矩 ⇒ ⭐ 那一半在 backtest/HANDOVER.md"
  exit 0
fi
note "⛔ 不通過：$FAIL 項"
note "⇒ ⛔ 在修好之前，⛔ 不要用這個環境跑任何一件登錄（跑出來的數字不可引用）"
exit 1

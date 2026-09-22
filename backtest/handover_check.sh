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
git config core.hooksPath .githooks && note "✅ core.hooksPath ＝ .githooks（⛔ 少了這行，壞掉的那一刻不會有人叫）"

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
  note "⇒ ⭐ 這證明的是【環境、資料、隨機源、引擎】四樣都對齊了"
  note "⛔ 它【不證明】接手的人懂這些規矩 ⇒ ⭐ 那一半在 backtest/HANDOVER.md"
  exit 0
fi
note "⛔ 不通過：$FAIL 項"
note "⇒ ⛔ 在修好之前，⛔ 不要用這個環境跑任何一件登錄（跑出來的數字不可引用）"
exit 1

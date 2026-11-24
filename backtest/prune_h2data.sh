#!/bin/bash
# 規則 19（使用者 2026-11-24「好」，回測 1124）：~/h2data 每晚名單快照只留最新 KEEP 份（daily_*、surgeaux_*），刪完清懸空 symlink。
#   這些都是 git archive 抽出的複本（正本在 tw-stock-data git 歷史），要用再由 run_daily_list.sh／surge_feat_daily.ensure_aux 重抽。
#   ⛔ 不碰 40 碼 sha 實體夾、研究快取（indrev_*、surge_*、full_*、mine_*、univ_*）、任何 *work 夾。
#   用法：prune_h2data.sh [正在用、不可刪的路徑 ...]；DRY=1 只列不刪；KEEP 預設 3
KEEP=${KEEP:-3}; H="$HOME/h2data"; DRY=${DRY:-0}
PROTECT=" $* "
n=0
for pfx in daily_ surgeaux_; do
  for d in $(ls -1dt "$H"/${pfx}*/ 2>/dev/null | tail -n +$((KEEP+1))); do
    d=${d%/}
    case "$PROTECT" in *" $d "*) continue;; esac
    if [ "$DRY" = 1 ]; then echo "would rm $d"; else chmod -R u+w "$d" && rm -rf "$d"; fi
    n=$((n+1))
  done
done
m=0
for l in $(find "$H" -maxdepth 1 -xtype l); do
  if [ "$DRY" = 1 ]; then echo "would unlink $l"; else rm -f "$l"; fi
  m=$((m+1))
done
echo "清快照 $n 份、懸空連結 $m 個｜h2data 現 $(du -sh "$H" 2>/dev/null | cut -f1)"

#!/bin/bash
set -e
S=/mnt/c/Users/ChemTim/AppData/Local/Temp/claude/59e7cc256a461904/f4c14e25-a422-4a37-ab64-e11f2ead97b5/scratchpad/scan64
date
$S/run.sh $S/panel.py 4 2>&1 | tail -5
date
$S/run.sh $S/factors.py 2>&1 | grep -v nonnan | tail -40
date
